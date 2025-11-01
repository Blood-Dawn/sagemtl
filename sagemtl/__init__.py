# Kheiven D''Haiti — lightweight package init
from __future__ import annotations

try:
    from importlib.metadata import version as _v

    __version__ = _v("sagemtl")
except Exception:
    __version__ = "0.0.0"
__all__ = ["__version__"]
