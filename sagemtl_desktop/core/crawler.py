"""
Legacy SageCrawler adapter has been removed.

This module remains only to avoid import-time crashes. Any attempt to
instantiate will raise to direct developers to use LightNovelCrawlerWrapper.
"""

class Crawler:
    def __init__(self):
        raise RuntimeError(
            "SageCrawler has been removed. Please use LightNovelCrawlerWrapper."
        )
        
