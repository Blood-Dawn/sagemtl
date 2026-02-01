"""Test configuration to ensure the package root is importable."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Configure pytest with custom settings and warning filters."""
    # Filter out known warnings from external libraries
    warnings.filterwarnings(
        "ignore",
        message="builtin type.*has no __module__ attribute",
        category=DeprecationWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message="pythonjsonlogger.jsonlogger has been moved",
        category=DeprecationWarning,
    )
