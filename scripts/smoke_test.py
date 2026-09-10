"""Does the app still start, and does it still get its numbers from the database.

    python scripts/smoke_test.py

This is the test that has to keep passing no matter what you change. It does not
check that your dashboard is any good — nothing automated can — it checks that a
stranger who clones this repository and follows the README gets a running page
instead of a stack trace.

It runs the real app through Streamlit's own test harness rather than importing
it, so a crash anywhere in the script is caught here rather than discovered by
whoever opens your URL. `AppTest` ships inside Streamlit; there is no test
framework to install.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "seed.db"

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    """`detail` is the message for a failure, so it only prints on one."""
    print(f"{'PASS ' if condition else 'FAIL '} {label}" + ("" if condition or not detail else f"  — {detail}"))
    if not condition:
        failures.append(label)


def main() -> int:
    check(
        "the source extract is committed",
        (ROOT / "data" / "library_loans.csv").exists(),
        "data/library_loans.csv is missing — a template with no data cannot be started",
    )
    check(
        "the database was built",
        DB_PATH.exists(),
        "run `python scripts/build_seed_db.py`",
    )
    if not DB_PATH.exists():
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check(
        "the four seed tables exist",
        {"branches", "patrons", "titles", "loans"} <= tables,
        f"found {sorted(tables)}",
    )

    # Every .sql file has to be valid SQL against the real schema. A typo in a
    # query is invisible until the page renders, and on a deployed app that
    # means a stranger finds it before you do.
    for path in sorted((ROOT / "queries").glob("*.sql")):
        try:
            conn.execute(path.read_text()).fetchall()
            check(f"queries/{path.name} runs", True)
        except sqlite3.Error as exc:
            check(f"queries/{path.name} runs", False, str(exc))
    conn.close()

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    check(
        "the app runs without raising",
        not app.exception,
        "; ".join(str(e.value) for e in app.exception),
    )
    check("the app renders a title", len(app.title) > 0)
    check(
        "the app reports its own freshness",
        any("refreshed" in c.value or "No pipeline run" in c.value for c in app.caption)
        or any("refreshed" in e.value for e in app.error)
        or any("refreshed" in w.value for w in app.warning),
        "nothing on the page says when the data last updated",
    )

    print()
    if failures:
        print(f"{len(failures)} smoke check(s) failed: " + ", ".join(failures))
        return 1
    print("Smoke checks passed. The scaffolding works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
