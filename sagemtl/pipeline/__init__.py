"""End-to-end pipeline for SageMTL.

This module provides the integrated workflow:
- Download -> Translate -> Export
- Library management
- Job queue and persistence
"""

from .workflow import (
    SageMTLPipeline,
    PipelineConfig,
    PipelineResult,
    PipelineStatus,
    run_pipeline,
)
from .library import (
    LibraryManager,
    NovelEntry,
    get_library,
)

__all__ = [
    # Pipeline
    "SageMTLPipeline",
    "PipelineConfig",
    "PipelineResult",
    "PipelineStatus",
    "run_pipeline",
    # Library
    "LibraryManager",
    "NovelEntry",
    "get_library",
]
