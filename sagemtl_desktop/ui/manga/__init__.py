"""PySide6 UI components for the SageMTL manga workspace.

The widgets here are implemented in Phase 8 (view, reader, source dialog) and
Phase 10 (typeset editor). UI logic stays thin: widgets call into
``sagemtl_desktop.core.manga`` and never hold business logic (see AGENTS.md).
This package init is intentionally empty so importing it does not pull in PySide6.
"""
