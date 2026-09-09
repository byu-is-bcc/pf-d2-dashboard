"""Pytest plumbing. Nothing here is part of the assignment.

The service resolves `data/` and `models/` relative to the working
directory, which is the repository root both locally and on every platform
in the deploy section. Pinning the working directory here means `pytest`
behaves the same whether you run it from the root or from inside `tests/`.
"""

import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
