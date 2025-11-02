"""Textual application entry points for SageMTL."""
from __future__ import annotations

from .app import SageMTLApp

__all__ = ["SageMTLApp", "run"]


def run() -> None:
    """Launch the SageMTL Textual user interface."""
    SageMTLApp().run()
