"""Build seed.db from library_loans.csv.

This file IS shipped, in both D1 and D2, as scripts/build_seed_db.py. It is the
one piece of the seed a student is allowed to read as an example, because it
shows the normalization the project is asking them to perform on their own data.

The flat CSV is one wide row per loan, with the title, subject, patron type and
branch repeated on every row. The database splits that into four tables. That
split is the point: after it, almost no interesting question can be answered
without a join, which is what D1 is teaching.

Usage:
    python scripts/build_seed_db.py                  # data/library_loans.csv -> data/seed.db
    python scripts/build_seed_db.py --force          # overwrite an existing seed.db
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "library_loans.csv"
DB_PATH = ROOT / "data" / "seed.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE branches (
    branch_id   INTEGER PRIMARY KEY,
    branch_name TEXT NOT NULL UNIQUE
);

CREATE TABLE patrons (
    patron_id   INTEGER PRIMARY KEY,
    patron_type TEXT NOT NULL
);

CREATE TABLE titles (
    title_id         INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    subject          TEXT NOT NULL,
    publication_year INTEGER NOT NULL
);

CREATE TABLE loans (
    loan_id       INTEGER PRIMARY KEY,
    title_id      INTEGER NOT NULL REFERENCES titles(title_id),
    patron_id     INTEGER NOT NULL REFERENCES patrons(patron_id),
    branch_id     INTEGER NOT NULL REFERENCES branches(branch_id),
    checkout_date TEXT NOT NULL,
    due_date      TEXT NOT NULL,
    return_date   TEXT,          -- NULL means never returned
    renewals      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_loans_checkout ON loans(checkout_date);
CREATE INDEX idx_loans_title    ON loans(title_id);
CREATE INDEX idx_loans_branch   ON loans(branch_id);
CREATE INDEX idx_loans_patron   ON loans(patron_id);
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing seed.db")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        raise SystemExit(f"missing {CSV_PATH.relative_to(ROOT)} — did you clone the whole repo?")

    if DB_PATH.exists():
        if not args.force:
            raise SystemExit(
                f"{DB_PATH.relative_to(ROOT)} already exists. Pass --force to rebuild it."
            )
        DB_PATH.unlink()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    with CSV_PATH.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    branches: dict[str, int] = {}
    patrons: dict[int, str] = {}
    titles: dict[int, tuple[str, str, int]] = {}

    for r in rows:
        if r["branch"] not in branches:
            branches[r["branch"]] = len(branches) + 1
        patrons.setdefault(int(r["patron_id"]), r["patron_type"])
        titles.setdefault(
            int(r["title_id"]),
            (r["title"], r["subject"], int(r["publication_year"])),
        )

    conn.executemany(
        "INSERT INTO branches (branch_id, branch_name) VALUES (?, ?)",
        [(bid, name) for name, bid in branches.items()],
    )
    conn.executemany(
        "INSERT INTO patrons (patron_id, patron_type) VALUES (?, ?)",
        sorted(patrons.items()),
    )
    conn.executemany(
        "INSERT INTO titles (title_id, title, subject, publication_year) VALUES (?, ?, ?, ?)",
        [(tid, *vals) for tid, vals in sorted(titles.items())],
    )
    conn.executemany(
        """INSERT INTO loans
           (loan_id, title_id, patron_id, branch_id, checkout_date, due_date, return_date, renewals)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                int(r["loan_id"]),
                int(r["title_id"]),
                int(r["patron_id"]),
                branches[r["branch"]],
                r["checkout_date"],
                r["due_date"],
                r["return_date"] or None,
                int(r["renewals"]),
            )
            for r in rows
        ],
    )
    conn.commit()

    print(f"built {DB_PATH.relative_to(ROOT)}")
    for table in ("branches", "patrons", "titles", "loans"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:9s} {n:>6,}")
    conn.close()


if __name__ == "__main__":
    main()
