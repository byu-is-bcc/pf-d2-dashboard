"""The dashboard.

    streamlit run app.py

Everything on the page comes from SQL in queries/ run against a SQLite
database. Nothing is hardcoded, and nothing is read from a CSV at page load.
Point DASHBOARD_DB at your D1 database and the same page renders against it.

The plumbing in here is finished: the connection, the query loader, the
freshness banner, the gate banner, the chart helper. The dashboard is not. Read
the DECIDE block below, then MAKE_IT_YOURS.md.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
QUERIES = ROOT / "queries"
STATE_PATH = ROOT / "data" / "refresh_state.json"
DB_PATH = Path(os.environ.get("DASHBOARD_DB", ROOT / "data" / "seed.db"))


# ==========================================================================
# DECIDE
#
# Five values, all None. The page runs with them unset and looks like a
# template with the labels still showing, which is the intended and only
# available default. There is nothing to passively inherit here.
#
# Fill them in, then write down why in MAKE_IT_YOURS.md. `python
# scripts/check_decisions.py` fails while any of them is still None, and so
# does the `dashboard (red until you finish it)` job in CI.
# ==========================================================================

# The name at the top of the page and in the browser tab. Not "Dashboard".
TITLE: str | None = None

# One sentence. The question a visitor gets an answer to by reading this page.
# If you cannot write it as a question, the page does not have a subject yet,
# it has a collection of charts.
QUESTION: str | None = None

# Who you built it for, in a few words. "A branch manager deciding summer
# hours" produces a different page than "a recruiter with 40 seconds", and
# both are legitimate. Naming one is what makes the layout decidable.
READER: str | None = None

# One hex color. There is no default and the charts render gray until you set
# it, the same way Project 000's stylesheet leaves --accent undefined.
#
# One color. An accent that appears on every element is not an accent, it is a
# second body color. Anything at body text size needs 4.5:1 contrast against
# white: https://webaim.org/resources/contrastchecker/
ACCENT: str | None = None

# The order the page renders in. Rename, reorder, delete, add. What ships is
# the order these were written in, which is not a design.
SECTIONS: list[str] = ["headline", "kpis", "seasonality", "returns"]

PLACEHOLDER_GRAY = "#9ca3af"
IS_TEMPLATE_DEFAULT = any(v is None for v in (TITLE, QUESTION, READER, ACCENT))


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """One read-only connection, reused across reruns.

    cache_resource rather than cache_data because a connection is a handle, not
    a value — Streamlit reruns this whole script top to bottom on every widget
    interaction, and opening a fresh connection each time is a leak with extra
    steps.

    Read-only is not paranoia. It is a promise to a reviewer that opening this
    page cannot change the numbers, which is the kind of thing that is cheap to
    guarantee now and impossible to prove later.
    """
    if not DB_PATH.exists():
        build_database()
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)


def build_database() -> None:
    """Build the database if it is missing.

    The database is a build output and gitignored, so a fresh deploy on
    Streamlit Community Cloud has the CSV and no .db. Rather than fail with a
    file-not-found that looks like a platform problem, build it.

    This is the seed path and it is a crutch. Once fetch() in scripts/refresh.py
    pulls from a real source, the refresh workflow owns building the database
    and this fallback should be reduced to an error message telling you the
    pipeline has not run.
    """
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_seed_db.py")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        st.error("Could not build the database.")
        st.code(result.stderr or result.stdout)
        st.stop()


def sql(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text()


@st.cache_data(ttl=600)
def query(name: str) -> pd.DataFrame:
    return pd.read_sql_query(sql(name), get_connection())


def load_state() -> dict | None:
    """What the last pipeline run found. Written by scripts/refresh.py."""
    if not STATE_PATH.exists():
        return None
    try:
        return json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# The page tells you its own state before it tells you anything else
# --------------------------------------------------------------------------


def hours_since(iso: str) -> float:
    stamp = datetime.fromisoformat(iso)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamp).total_seconds() / 3600


def render_pipeline_status(state: dict | None) -> bool:
    """Draw the freshness and gate banners. Returns True when numbers are safe to show.

    This function is the reason this project is Practitioner tier rather than a
    charting exercise. A dashboard that cannot describe its own condition will,
    on the day its source breaks, show a wrong number in a large font with no
    caveat, and someone will act on it. Being visibly broken beats being
    quietly wrong.
    """
    if state is None:
        st.warning(
            "**No pipeline run on record.** Nothing has verified this data. "
            "Run `python scripts/refresh.py` and commit `data/refresh_state.json`."
        )
        return True

    age = hours_since(state["run_finished_at"])
    if age < 1:
        when = "less than an hour ago"
    elif age < 48:
        when = f"{age:.0f} hours ago"
    else:
        when = f"{age / 24:.1f} days ago"
    stamp = f"Data refreshed **{when}** ({state['run_finished_at']} UTC) from {state['source']}."

    failed = [c for c in state["checks"] if c["status"] != "pass"]
    blocking = [c for c in failed if c["severity"] == "blocking"]

    # Staleness. The thresholds are hours, not vibes, and they are here rather
    # than in checks.toml because this is about the published page rather than
    # about the data: a gate that ran successfully yesterday says nothing about
    # whether today's run ever happened.
    if age > 24 * 7:
        st.error(f"{stamp} That is over a week. Assume the refresh is broken.")
    elif age > 36:
        st.warning(f"{stamp} The schedule is daily, so this run is overdue.")
    else:
        st.caption(stamp)

    if blocking:
        names = ", ".join(f"`{c['name']}`" for c in blocking)
        st.error(
            f"**{len(blocking)} blocking data quality gate(s) failed: {names}.** "
            "The numbers on this page are being withheld rather than shown, because a "
            "number drawn from data that failed its own checks is worse than no number.",
            icon=":material/block:",
        )
        with st.expander("What failed"):
            for c in blocking:
                st.markdown(f"- **{c['name']}** — {c['detail']}")
        return False

    if failed:
        with st.expander(f"{len(failed)} non-blocking quality warning(s)"):
            for c in failed:
                st.markdown(f"- **{c['name']}** ({c['status']}) — {c['detail']}")

    return True


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------


def color() -> str:
    return ACCENT or PLACEHOLDER_GRAY


def chart_title(finding: str, *, placeholder: bool = False) -> str:
    """A chart title is a sentence, not a pair of axis names.

    This is the D0 rule carried forward. "Revenue by day of week" describes the
    picture. "Saturday earns 40% more than any weekday" is the thing you want
    the reader to walk away with, and the picture underneath is the evidence
    for it. If you cannot write the title as a claim, you have not found the
    finding yet, you have only made a chart.
    """
    return f"[axis labels, not a finding] {finding}" if placeholder else finding


def month_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_line(point=True, color=color())
        .encode(
            x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("loans:Q", title="Loans"),
            tooltip=["month", "loans"],
        )
        .properties(
            height=280,
            title=chart_title("Loans per month, September 2024 to August 2026", placeholder=True),
        )
    )


def returns_chart(df: pd.DataFrame) -> alt.Chart:
    melted = df.melt(
        id_vars="patron_type",
        value_vars=["pct_never_returned", "pct_returned_late"],
        var_name="outcome",
        value_name="pct",
    ).replace({"pct_never_returned": "Never returned", "pct_returned_late": "Returned late"})

    # One accent and one gray. Two full-strength colors on a two-series chart
    # makes the reader decide which one matters; picking for them is the job.
    scale = alt.Scale(
        domain=["Never returned", "Returned late"], range=[color(), PLACEHOLDER_GRAY]
    )
    return (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("patron_type:N", title=None, sort="-y"),
            y=alt.Y("pct:Q", title="Percent of that group's loans"),
            color=alt.Color("outcome:N", scale=scale, title=None),
            xOffset="outcome:N",
            tooltip=["patron_type", "outcome", "pct"],
        )
        .properties(
            height=280,
            title=chart_title("Return outcomes by patron type", placeholder=True),
        )
    )


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


def section_headline(safe: bool) -> None:
    row = query("headline").iloc[0]
    if row["value"] is None or pd.isna(row["value"]):
        st.info(
            "**The headline number is unwritten.** `queries/headline.sql` returns NULL. "
            "This slot is the first thing anyone reads and it is currently empty.",
            icon=":material/edit_note:",
        )
        return
    st.metric(row["label"], row["value"])


def section_kpis(safe: bool) -> None:
    if not safe:
        st.subheader("Summary")
        cols = st.columns(4)
        for col, label in zip(cols, ["Loans", "Patrons", "Never returned", "Returned late"]):
            col.metric(label, "—", help="Withheld: a blocking quality gate failed.")
        return

    k = query("kpis").iloc[0]
    cols = st.columns(4)
    cols[0].metric("Loans", f"{k.total_loans:,}")
    cols[1].metric("Patrons", f"{k.distinct_patrons:,}")
    cols[2].metric("Never returned", f"{k.never_returned:,}")
    cols[3].metric("Returned late", f"{k.returned_late:,}")


def section_seasonality(safe: bool) -> None:
    if not safe:
        return
    st.altair_chart(month_chart(query("loans_by_month")), width="stretch")


def section_returns(safe: bool) -> None:
    if not safe:
        return
    st.altair_chart(returns_chart(query("returns_by_patron_type")), width="stretch")


SECTION_RENDERERS = {
    "headline": section_headline,
    "kpis": section_kpis,
    "seasonality": section_seasonality,
    "returns": section_returns,
}


# --------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title=TITLE or "Unnamed dashboard (template default)",
        layout="wide",
    )

    if IS_TEMPLATE_DEFAULT:
        st.error(
            "**This is the template, deployed unchanged.** The title, the question, the "
            "reader and the accent color are all still unset in `app.py`, so this page has "
            "no subject and no visual hierarchy. Open `MAKE_IT_YOURS.md`.",
            icon=":material/warning:",
        )

    st.title(TITLE or "Unnamed dashboard")
    if QUESTION:
        st.markdown(f"**{QUESTION}**")
    else:
        st.markdown(":gray[_The question this page answers is unwritten. See `app.py`._]")

    safe = render_pipeline_status(load_state())
    st.divider()

    for name in SECTIONS:
        SECTION_RENDERERS[name](safe)

    st.divider()
    state = load_state()
    source = state["source"] if state else "unknown"
    rows = f"{state['loan_rows']:,}" if state else "unknown"
    span = f"{state['oldest_checkout']} to {state['newest_checkout']}" if state else "unknown"
    st.caption(
        f"{rows} loans covering {span}. Source: {source}. "
        f"Built for: {READER or 'nobody in particular yet'}. "
        "Every number on this page comes from SQL in `queries/`."
    )


if __name__ == "__main__":
    main()
