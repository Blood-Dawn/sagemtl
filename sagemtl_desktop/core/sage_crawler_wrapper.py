"""
SageCrawler has been removed.

This module is intentionally left as a stub to avoid imports breaking.
All crawling functionality now uses lightnovel-crawler exclusively.
"""

from sagemtl_desktop.core.crawler_interface import CrawlerInterface


class SageCrawlerWrapper(CrawlerInterface):
    def __init__(self):
        raise RuntimeError(
            "SageCrawler has been removed. Use LightNovelCrawlerWrapper instead."
        )

