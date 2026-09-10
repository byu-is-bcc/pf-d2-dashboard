"""The scheduled refresh. Fetch, rebuild, gate, record.

`.github/workflows/refresh.yml` runs this once a day. Nothing here needs a
human. That is the whole idea: the difference between a dashboard and a
screenshot is that one of them is still true tomorrow.

    python scripts/refresh.py            # the full pipeline
    python scripts/refresh.py --dry-run  # run it without writing refresh_state.json

Four steps, in this order, and the order matters:

    1. fetch    pull the source. For the shipped seed this is a local file.
    2. build    rebuild data/seed.db from the source
    3. gate     run scripts/checks.py
    4. record   write data/refresh_state.json — including failures

Step 4 happens whether or not step 3 passed, and that is the part students skip.
A pipeline that dies silently on a bad day leaves the dashboard showing last
week's numbers with no indication that anything went wrong, which is worse than
showing nothing. The dashboard reads refresh_state.json, so a failed run is
visible on the page within one deploy instead of never.

The process exits non-zero when a blocking gate failed. GitHub emails you when
a scheduled workflow fails. That email is the alerting system, and it is free.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "library_loans.csv"
DB_PATH = ROOT / "data" / "seed.db"
STATE_PATH = ROOT / "data" / "refresh_state.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch() -> str:
    """Get the current source data onto disk. Returns a label for where it came from.

    TODO — this is the seam where your project stops being the template.

    Right now this function checks that the committed CSV is where it should be
    and returns. It does not fetch anything, because the shipped seed is a fixed
    20,000-row extract that will say exactly the same thing tomorrow. Run the
    pipeline against it a hundred times and the dashboard never changes.

    That is fine for getting the plumbing working and it is not fine as a
    portfolio piece. "Scheduled refresh" against a file that never changes is a
    cron job with nothing to do, and a reviewer will ask.

    Replace the body with a real pull. Some sources that are free, public, and
    genuinely move:

      - a city or state open data portal with a CSV or JSON export endpoint
        (most Socrata portals will hand you the whole dataset over HTTP)
      - a public API with no key: USGS earthquakes, NWS weather observations,
        GTFS transit feeds, Wikipedia pageviews
      - GitHub's own API, for a repository or org you care about
      - your own database from D1, if it is somewhere this workflow can reach it

    Whatever you pick, this function should end with the source data written to
    disk where step 2 can find it, and it should raise on failure rather than
    returning stale data. A fetch that swallows a 500 and leaves yesterday's
    file in place is the single most common way a "refreshing" dashboard stops
    refreshing without telling anyone.
    """
    if not CSV_PATH.exists():
        raise SystemExit(
            f"missing {CSV_PATH.relative_to(ROOT)} — did you clone the whole repo?"
        )
    size_mb = CSV_PATH.stat().st_size / 1_000_000
    print(f"[fetch] {CSV_PATH.relative_to(ROOT)} ({size_mb:.1f} MB, committed, does not change)")
    return "committed seed extract (data/library_loans.csv)"


def build() -> None:
    """Rebuild the database from the source, from scratch, every time.

    Not an incremental update. Rebuilding is slower and it is worth it here,
    because an incremental pipeline that drifts from its source is a bug you
    cannot see: the database is internally consistent and simply wrong. At
    20,000 rows a full rebuild takes about a second. Buy the certainty.
    """
    print("[build] rebuilding data/seed.db")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_seed_db.py"), "--force"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit("[build] failed — the database was not rebuilt")
    print("\n".join("  " + line for line in result.stdout.strip().splitlines()))


def snapshot(db_path: Path) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
        newest = conn.execute("SELECT MAX(checkout_date) FROM loans").fetchone()[0]
        oldest = conn.execute("SELECT MIN(checkout_date) FROM loans").fetchone()[0]
        return {"loan_rows": rows, "oldest_checkout": oldest, "newest_checkout": newest}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="do not write refresh_state.json")
    parser.add_argument("--suite", choices=["core", "student", "all"], default="core")
    args = parser.parse_args()

    started_at = now()
    previous = checks.load_previous_state(STATE_PATH)

    source = fetch()
    build()

    print("[gate] running the quality checks")
    results = checks.run(DB_PATH, args.suite, previous)
    checks.report(results)

    blocked = [r for r in results if r.blocks]
    state = {
        "run_started_at": started_at,
        "run_finished_at": now(),
        "source": source,
        "status": "blocked" if blocked else "ok",
        "suite": args.suite,
        **snapshot(DB_PATH),
        "checks": [asdict(r) for r in results],
    }

    if args.dry_run:
        print("[record] --dry-run, not writing refresh_state.json")
    else:
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
        print(f"[record] wrote {STATE_PATH.relative_to(ROOT)} with status={state['status']}")

    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
