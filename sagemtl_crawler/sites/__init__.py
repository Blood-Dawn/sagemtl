"""Site adapters for SageCrawler

This module provides adapters for various web novel sites.
Each adapter implements the same protocol for searching, fetching TOC, and downloading chapters.
"""

from .fanmtl import FanMTLAdapter
from .wuxiaworld import WuxiaworldAdapter
from .webnovel import WebnovelAdapter
from .novelupdates import NovelUpdatesAdapter
from .royalroad import RoyalRoadAdapter
from .scribblehub import ScribbleHubAdapter
from .lnmtl import LNMTLAdapter

__all__ = [
    "FanMTLAdapter",
    "WuxiaworldAdapter",
    "WebnovelAdapter",
    "NovelUpdatesAdapter",
    "RoyalRoadAdapter",
    "ScribbleHubAdapter",
    "LNMTLAdapter",
]
