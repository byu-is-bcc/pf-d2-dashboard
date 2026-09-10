"""Data quality gates. Run these before anything gets published.

The point of this file is not that bad data is impossible. It is that bad data
is *loud*. A dashboard with no gates does not fail when the source breaks. It
redraws every chart against half the rows and shows you a confident number, and
you find out three weeks later when someone asks why March moved.

Run the gates:

    python scripts/checks.py                  # core suite, against data/seed.db
    python scripts/checks.py --suite all      # core + the ones you have to write
    python scripts/checks.py --db path/to.db  # your D1 database instead

See what a failure looks like, without breaking your real database:

    python scripts/checks.py --demo-failure

Exit code is 0 when no blocking gate failed and 1 when one did. That is what
makes the refresh workflow go red instead of publishing quietly.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "seed.db"
CONFIG_PATH = ROOT / "checks.toml"

PASS = "pass"
FAIL = "fail"
NOT_CONFIGURED = "not_configured"

BLOCKING = "blocking"
WARNING = "warning"


@dataclass
class Result:
    name: str
    suite: str
    severity: str
    status: str
    detail: str

    @property
    def blocks(self) -> bool:
        return self.severity == BLOCKING and self.status != PASS


# --------------------------------------------------------------------------
# The core suite. These are finished and they are supposed to pass. If one of
# them goes red on a clean clone you broke the scaffolding, not the assignment.
# --------------------------------------------------------------------------


def check_loan_row_count(conn, cfg, state) -> Result:
    floor = cfg["core"]["min_loan_rows"]
    n = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    ok = n >= floor
    return Result(
        "loan_row_count",
        "core",
        BLOCKING,
        PASS if ok else FAIL,
        f"{n:,} loan rows against a floor of {floor:,}",
    )


def check_row_count_drift(conn, cfg, state) -> Result:
    """Compare this run's row count against the last one that published.

    A truncated extract usually still has thousands of rows, so it sails past a
    floor. What gives it away is the size of the jump.
    """
    limit = cfg["core"]["max_row_drift_pct"]
    n = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    previous = (state or {}).get("loan_rows")

    if not previous:
        return Result(
            "row_count_drift",
            "core",
            WARNING,
            PASS,
            f"{n:,} rows, no previous run on record to compare against",
        )

    drift = abs(n - previous) / previous * 100
    ok = drift <= limit
    return Result(
        "row_count_drift",
        "core",
        BLOCKING,
        PASS if ok else FAIL,
        f"{previous:,} -> {n:,} rows, {drift:.1f}% change against a {limit:.1f}% limit",
    )


def check_required_fields_not_null(conn, cfg, state) -> Result:
    """Nulls in columns that carry meaning.

    `loans.return_date` is missing from this list on purpose. A null there means
    the book was never brought back, which is one of the more interesting things
    in the data. Knowing which nulls are defects and which are information is
    the judgement this gate is really testing.
    """
    required = [
        ("loans", "title_id"),
        ("loans", "patron_id"),
        ("loans", "branch_id"),
        ("loans", "checkout_date"),
        ("loans", "due_date"),
        ("titles", "title"),
        ("titles", "subject"),
        ("branches", "branch_name"),
        ("patrons", "patron_type"),
    ]
    offenders = []
    for table, column in required:
        n = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR TRIM({column}) = ''"
        ).fetchone()[0]
        if n:
            offenders.append(f"{table}.{column} ({n:,})")

    return Result(
        "required_fields_not_null",
        "core",
        BLOCKING,
        PASS if not offenders else FAIL,
        f"{len(required)} columns clean"
        if not offenders
        else "empty values in " + ", ".join(offenders),
    )


def check_referential_integrity(conn, cfg, state) -> Result:
    """Every foreign key in `loans` resolves to a row that exists.

    SQLite will happily store a loan pointing at a title_id that was never
    inserted unless foreign keys are switched on for that connection, and they
    are off by default. An orphan does not error. It just quietly drops out of
    every join you write, so your totals shrink and nothing says why.
    """
    orphans = []
    for column, parent, key in [
        ("title_id", "titles", "title_id"),
        ("patron_id", "patrons", "patron_id"),
        ("branch_id", "branches", "branch_id"),
    ]:
        n = conn.execute(
            f"""SELECT COUNT(*) FROM loans l
                LEFT JOIN {parent} p ON l.{column} = p.{key}
                WHERE p.{key} IS NULL"""
        ).fetchone()[0]
        if n:
            orphans.append(f"{n:,} loans with no matching {parent} row")

    return Result(
        "referential_integrity",
        "core",
        BLOCKING,
        PASS if not orphans else FAIL,
        "every loan resolves to a title, a patron and a branch"
        if not orphans
        else "; ".join(orphans),
    )


def check_loan_id_unique(conn, cfg, state) -> Result:
    total, distinct = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT loan_id) FROM loans"
    ).fetchone()
    ok = total == distinct
    return Result(
        "loan_id_unique",
        "core",
        BLOCKING,
        PASS if ok else FAIL,
        f"{total:,} rows, {distinct:,} distinct loan_id"
        + ("" if ok else f" — {total - distinct:,} duplicated"),
    )


def check_date_ordering(conn, cfg, state) -> Result:
    """Dates that run backwards.

    A due date before its checkout date is impossible, and a row like that makes
    every "days overdue" number you compute from it garbage in a way that is
    invisible once it is averaged with 20,000 others.
    """
    problems = []
    n = conn.execute("SELECT COUNT(*) FROM loans WHERE due_date < checkout_date").fetchone()[0]
    if n:
        problems.append(f"{n:,} loans due before they were checked out")
    n = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE return_date IS NOT NULL AND return_date < checkout_date"
    ).fetchone()[0]
    if n:
        problems.append(f"{n:,} loans returned before they were checked out")

    return Result(
        "date_ordering",
        "core",
        BLOCKING,
        PASS if not problems else FAIL,
        "checkout <= due, checkout <= return everywhere"
        if not problems
        else "; ".join(problems),
    )


def check_no_future_checkouts(conn, cfg, state) -> Result:
    today = datetime.now(timezone.utc).date().isoformat()
    n = conn.execute("SELECT COUNT(*) FROM loans WHERE checkout_date > ?", (today,)).fetchone()[0]
    return Result(
        "no_future_checkouts",
        "core",
        WARNING,
        PASS if n == 0 else FAIL,
        f"no checkout_date after {today}" if n == 0 else f"{n:,} loans checked out in the future",
    )


def check_categorical_domain(conn, cfg, state) -> Result:
    """The set of values a grouping column is allowed to take.

    This is the gate people skip and then wish they had. Every chart on the
    dashboard that splits by patron type assumes there are four of them. The day
    the source system adds "Alumni", nothing breaks, nothing errors, and every
    percentage on the page is now computed over a different denominator.
    """
    allowed = set(cfg["core"]["patron_types"])
    found = {r[0] for r in conn.execute("SELECT DISTINCT patron_type FROM patrons")}
    unexpected = sorted(found - allowed)
    missing = sorted(allowed - found)

    notes = []
    if unexpected:
        notes.append("unexpected: " + ", ".join(unexpected))
    if missing:
        notes.append("declared but absent: " + ", ".join(missing))

    return Result(
        "categorical_domain",
        "core",
        BLOCKING if unexpected else WARNING,
        PASS if not notes else FAIL,
        f"patron_type holds exactly the {len(allowed)} declared values"
        if not notes
        else "; ".join(notes),
    )


# --------------------------------------------------------------------------
# The student suite. These ship failing. They are the assignment.
# --------------------------------------------------------------------------


def check_data_recency(conn, cfg, state) -> Result:
    """How stale is the newest row allowed to get.

    The threshold is not in this file because it is not a property of the code.
    It is a claim about your source, and only you know your source. Set
    max_data_age_days in checks.toml.
    """
    limit = cfg.get("student", {}).get("max_data_age_days")
    newest = conn.execute("SELECT MAX(checkout_date) FROM loans").fetchone()[0]

    if limit is None:
        return Result(
            "data_recency",
            "student",
            BLOCKING,
            NOT_CONFIGURED,
            f"newest row is {newest}, but max_data_age_days is unset in checks.toml — "
            "decide what stale means for your source and set it",
        )

    age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(newest).date()).days
    ok = age <= limit
    return Result(
        "data_recency",
        "student",
        BLOCKING,
        PASS if ok else FAIL,
        f"newest row is {newest}, {age} days old, against a {limit} day limit",
    )


def check_your_own_gate(conn, cfg, state) -> Result:
    """TODO — write one gate the template does not have.

    Not another row count. A gate that encodes something *your* dashboard
    depends on being true, which someone who has not read your SQL would not
    think to check. Some shapes that work, none of which you should copy
    verbatim, because the point is that yours comes from your own data:

      - a metric bounded by arithmetic (a rate that must sit between 0 and 1,
        a subtotal that must sum to its total)
      - a segment that must never be empty, because a chart that groups by it
        renders an empty panel and looks like a styling bug rather than a
        data outage
      - a relationship that must hold across two tables (every branch that
        appears in `loans` also appears in `branches` with a usable name)
      - a distribution that must not collapse (if 98% of loans land on one
        branch, the branch field has probably stopped being populated)

    Delete this whole body and write the check. Return a Result with status
    PASS when the condition holds and FAIL when it does not, and put the actual
    numbers in the detail string — a gate that reports "failed" and no numbers
    sends you back to the database to find out what happened, which is exactly
    the work the gate was supposed to save you.
    """
    return Result(
        "your_own_gate",
        "student",
        BLOCKING,
        FAIL,
        "not written yet — see the docstring in check_your_own_gate() in scripts/checks.py",
    )


CORE_CHECKS = [
    check_loan_row_count,
    check_row_count_drift,
    check_required_fields_not_null,
    check_referential_integrity,
    check_loan_id_unique,
    check_date_ordering,
    check_no_future_checkouts,
    check_categorical_domain,
]

STUDENT_CHECKS = [
    check_data_recency,
    check_your_own_gate,
]


# --------------------------------------------------------------------------


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_previous_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def run(db_path: Path, suite: str = "core", state: dict | None = None) -> list[Result]:
    if not db_path.exists():
        raise SystemExit(
            f"no database at {db_path} — run `python scripts/build_seed_db.py` first"
        )

    cfg = load_config()
    checks = {
        "core": CORE_CHECKS,
        "student": STUDENT_CHECKS,
        "all": CORE_CHECKS + STUDENT_CHECKS,
    }[suite]

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        results = []
        for check in checks:
            try:
                results.append(check(conn, cfg, state))
            except Exception as exc:  # a gate that crashes is a gate that failed
                results.append(
                    Result(check.__name__, "core", BLOCKING, FAIL, f"gate raised {exc!r}")
                )
        return results
    finally:
        conn.close()


SYMBOL = {PASS: "PASS", FAIL: "FAIL", NOT_CONFIGURED: "UNSET"}


def report(results: list[Result], stream=sys.stdout) -> None:
    width = max(len(r.name) for r in results)
    for r in results:
        marker = "!" if r.blocks else " "
        print(f"{marker} {SYMBOL[r.status]:5s}  {r.name:<{width}}  {r.detail}", file=stream)

    blocked = [r for r in results if r.blocks]
    warned = [r for r in results if r.status != PASS and not r.blocks]
    print("", file=stream)
    if blocked:
        print(
            f"{len(blocked)} blocking gate(s) failed: "
            + ", ".join(r.name for r in blocked)
            + "\nNothing should publish off this database until that is fixed.",
            file=stream,
        )
    elif warned:
        print(f"{len(warned)} warning(s), nothing blocking.", file=stream)
    else:
        print(f"All {len(results)} gates passed.", file=stream)


def demo_failure(db_path: Path) -> int:
    """Damage a throwaway copy of the database and run the gates against it.

    Your real database is not touched. The point is that you should see what a
    red run looks like before it happens to you at 6am on a Tuesday.
    """
    if not db_path.exists():
        raise SystemExit(f"no database at {db_path} — run `python scripts/build_seed_db.py` first")

    with tempfile.TemporaryDirectory() as tmp:
        broken = Path(tmp) / "broken.db"
        shutil.copy(db_path, broken)
        conn = sqlite3.connect(broken)
        conn.executescript(
            """
            -- an export that half-loaded
            DELETE FROM loans WHERE loan_id > 6000;
            -- a column the upstream system stopped populating
            UPDATE loans SET due_date = '' WHERE loan_id % 7 = 0;
            -- a loan pointing at a branch that does not exist
            UPDATE loans SET branch_id = 99 WHERE loan_id = 12;
            -- a category nobody told you about
            UPDATE patrons SET patron_type = 'Alumni' WHERE patron_id % 50 = 0;
            """
        )
        conn.commit()
        conn.close()

        print("Running the core gates against a deliberately damaged copy.")
        print(f"Your real database at {db_path.relative_to(ROOT)} is untouched.\n")
        results = run(broken, "core", state={"loan_rows": 20000})
        report(results)
        return 1 if any(r.blocks for r in results) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="database to check")
    parser.add_argument("--suite", choices=["core", "student", "all"], default="core")
    parser.add_argument("--json", type=Path, help="write the results to this path as JSON")
    parser.add_argument(
        "--demo-failure",
        action="store_true",
        help="run the gates against a damaged throwaway copy so you can see them fire",
    )
    args = parser.parse_args()

    if args.demo_failure:
        return demo_failure(args.db)

    state = load_previous_state(ROOT / "data" / "refresh_state.json")
    results = run(args.db, args.suite, state)
    report(results)

    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n")

    return 1 if any(r.blocks for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
