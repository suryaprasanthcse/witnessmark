#!/usr/bin/env python3
"""Witnessmark entry point: python wm.py <command>.

Puts core/ on the import path, so nothing needs installing. The core uses only
the Python standard library.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))

from witnessmark.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
