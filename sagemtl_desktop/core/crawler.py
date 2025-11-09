"""
Novel crawler using SageCrawler with automatic chapter detection.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Callable, Optional

from sagemtl.crawl.novel_crawler import NovelCrawler


class Crawler:
    """Wrapper for SageCrawler - built-in novel crawler with pattern detection"""

    def __init__(self):
        self.output_dir = Path(tempfile.mkdtemp(prefix="sagemtl_crawl_"))
        self.crawler = NovelCrawler()

    def is_available(self) -> bool:
        """SageCrawler is always available"""
        return True

    def crawl_novel(
        self,
        url: str,
        novel_name: str = "",
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Crawl novel using SageCrawler.

        Args:
            url: Novel URL
            novel_name: Name for the novel (optional)
            start_chapter: Starting chapter (optional)
            end_chapter: Ending chapter (optional)
            progress_callback: Progress callback (0-100)
            log_callback: Log callback (level, message)

        Returns:
            Path to generated text file containing chapters

        Raises:
            RuntimeError: If crawl fails
        """
        if log_callback:
            log_callback("info", f"Starting SageCrawler: {url}")

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            if log_callback:
                log_callback("info", "Detecting chapter pattern...")

            # Run the crawler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                novel_info = loop.run_until_complete(
                    self.crawler.crawl_novel(
                        start_url=url,
                        start_chapter=start_chapter or 1,
                        end_chapter=end_chapter or 999,
                        dataset_name=novel_name or "novel"
                    )
                )
            finally:
                loop.close()

            if log_callback:
                log_callback("info", f"Found {len(novel_info.chapters)} chapters")

            # Save to dataset
            dataset_path = self.crawler.save_to_dataset(
                novel_info,
                self.output_dir,
                format="txt"
            )

            if log_callback:
                log_callback("info", f"Saved to: {dataset_path}")

            if progress_callback:
                progress_callback(100.0)

            return str(dataset_path)

        except Exception as e:
            if log_callback:
                log_callback("error", f"Crawl error: {str(e)}")
            raise RuntimeError(f"SageCrawler failed: {str(e)}")

    def cleanup(self):
        """Clean up temp directory"""
        if self.output_dir.exists():
            import shutil
            try:
                shutil.rmtree(self.output_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp directory: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()
