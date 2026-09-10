"""The anti-sameness gate. Fails while this repo is still the template.

    python scripts/check_decisions.py

Several hundred students start from this file. A dashboard is the one artifact
in the catalog a recruiter actually opens and looks at, and the fourth identical
library dashboard someone sees in a day gets four seconds and a back button.
Everything checked here is something the template deliberately refuses to decide
for you.

This is the mechanical half. It reads what is in the files and cannot tell
whether your reasoning is any good. The other half is MAKE_IT_YOURS.md, which is
where you write the reasoning down, and an alumni reviewer reads that.

CI runs this in the `dashboard (red until you finish it)` job. It is supposed to
be red when you start.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
DECISIONS = ROOT / "MAKE_IT_YOURS.md"
CHECKS_PY = ROOT / "scripts" / "checks.py"
CHECKS_TOML = ROOT / "checks.toml"
HEADLINE_SQL = ROOT / "queries" / "headline.sql"

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def module_constants(path: Path) -> dict[str, object]:
    """Read module-level literal assignments without importing the module.

    Importing app.py would start pulling in Streamlit and would run whatever the
    student has added at module scope. Parsing is cheaper and cannot have side
    effects.
    """
    tree = ast.parse(path.read_text())
    found: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets, value = [node.target.id], node.value
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        else:
            continue
        for name in targets:
            try:
                found[name] = ast.literal_eval(value) if value is not None else None
            except ValueError:
                found[name] = "<not a literal>"
    return found


def main() -> int:
    app = module_constants(APP)
    decisions = DECISIONS.read_text()
    checks_src = CHECKS_PY.read_text()
    headline = HEADLINE_SQL.read_text()
    config = tomllib.loads(CHECKS_TOML.read_text())

    accent = app.get("ACCENT")

    results: list[tuple[bool, str, str]] = [
        (
            app.get("TITLE") not in (None, "", "<not a literal>"),
            "TITLE is set in app.py",
            "the page has no name, so the browser tab and the heading both say "
            '"Unnamed dashboard"',
        ),
        (
            app.get("QUESTION") not in (None, "", "<not a literal>"),
            "QUESTION is set in app.py",
            "the page does not state what it answers, which means it is a pile of "
            "charts rather than a dashboard",
        ),
        (
            app.get("READER") not in (None, "", "<not a literal>"),
            "READER is set in app.py",
            "you have not named who this is for, and layout decisions are not "
            "decidable until you do",
        ),
        (
            isinstance(accent, str) and bool(HEX.match(accent)),
            "ACCENT is a hex color in app.py",
            "every chart is rendering in placeholder gray",
        ),
        (
            "TODO" not in decisions,
            "MAKE_IT_YOURS.md has no TODO left in it",
            "the decision record is unwritten, so nothing above is a decision yet, "
            "it is just a value",
        ),
        (
            "placeholder=True" not in APP.read_text(),
            "no chart title is still marked as a placeholder",
            "at least one chart is titled with its axes instead of its finding — "
            "the D0 rule, carried forward",
        ),
        (
            "NULL AS value" not in headline,
            "queries/headline.sql returns a real number",
            "the first thing a visitor reads is still an empty slot",
        ),
        (
            "max_data_age_days" in config.get("student", {}),
            "max_data_age_days is set in checks.toml",
            "you have not decided how stale your data is allowed to get, so the "
            "data_recency gate cannot run",
        ),
        (
            "see the docstring in check_your_own_gate()" not in checks_src,
            "check_your_own_gate() in scripts/checks.py is written",
            "you have not added a single quality gate the template did not give you",
        ),
    ]

    width = max(len(label) for _, label, _ in results)
    failures = 0
    for ok, label, why in results:
        print(f"{'PASS ' if ok else 'FAIL '} {label:<{width}}" + ("" if ok else f"  — {why}"))
        failures += not ok

    print()
    if failures:
        print(
            f"{failures} of {len(results)} still at the template default.\n"
            "This repository would deploy, and it would look like everybody else's.\n"
            "MAKE_IT_YOURS.md is where you work through it."
        )
        return 1

    print(f"All {len(results)} decisions made. Now go read MAKE_IT_YOURS.md and check it is true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
