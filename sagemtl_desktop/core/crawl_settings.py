"""
Runtime crawl settings used by wrapper and generic fallback paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


DEFAULT_CRAWL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 SageMTL/2.0"
)


@dataclass
class CrawlSettings:
    """
    Per-site crawl settings.
    """

    request_delay_seconds: float = 0.0
    user_agent: str = DEFAULT_CRAWL_USER_AGENT
    max_retries: int = 2
    ignore_robots_txt: bool = False
    chapter_download_workers: int = 4
    resume_existing: bool = True
    auto_export_epub: bool = False
    epub_output_dir: str = ""

    def normalize(self) -> "CrawlSettings":
        self.request_delay_seconds = max(0.0, float(self.request_delay_seconds))
        self.max_retries = max(0, int(self.max_retries))
        self.chapter_download_workers = max(1, int(self.chapter_download_workers))
        if not self.user_agent.strip():
            self.user_agent = DEFAULT_CRAWL_USER_AGENT
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_delay_seconds": self.request_delay_seconds,
            "user_agent": self.user_agent,
            "max_retries": self.max_retries,
            "ignore_robots_txt": self.ignore_robots_txt,
            "chapter_download_workers": self.chapter_download_workers,
            "resume_existing": self.resume_existing,
            "auto_export_epub": self.auto_export_epub,
            "epub_output_dir": self.epub_output_dir,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any] | None) -> "CrawlSettings":
        if not isinstance(raw, dict):
            return cls()
        settings = cls(
            request_delay_seconds=raw.get("request_delay_seconds", 0.0),
            user_agent=raw.get("user_agent", DEFAULT_CRAWL_USER_AGENT),
            max_retries=raw.get("max_retries", 2),
            ignore_robots_txt=bool(raw.get("ignore_robots_txt", False)),
            chapter_download_workers=raw.get("chapter_download_workers", 4),
            resume_existing=bool(raw.get("resume_existing", True)),
            auto_export_epub=bool(raw.get("auto_export_epub", False)),
            epub_output_dir=raw.get("epub_output_dir", ""),
        )
        return settings.normalize()
