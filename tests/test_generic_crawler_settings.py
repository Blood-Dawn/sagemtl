"""Tests for generic crawler runtime settings behavior."""

from __future__ import annotations

import httpx
import pytest

from sagemtl_desktop.core.crawl_settings import CrawlSettings
from sagemtl_desktop.core.generic_crawler import GenericNovelCrawler


def test_generic_crawler_applies_user_agent_header():
    settings = CrawlSettings(user_agent="SageMTL-TestAgent/1.0", ignore_robots_txt=True)
    crawler = GenericNovelCrawler("https://example.com/novel", crawl_settings=settings)
    try:
        assert crawler.session.headers["User-Agent"] == "SageMTL-TestAgent/1.0"
    finally:
        crawler.close()


def test_request_retries_on_timeout(monkeypatch):
    settings = CrawlSettings(max_retries=2, ignore_robots_txt=True)
    crawler = GenericNovelCrawler("https://example.com/novel", crawl_settings=settings)
    call_count = {"value": 0}

    def fake_request(method, url, **kwargs):
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise httpx.TimeoutException("timeout")
        request = httpx.Request(method, url)
        return httpx.Response(200, request=request, text="ok")

    monkeypatch.setattr(crawler.session, "request", fake_request)
    try:
        response = crawler._request("GET", "https://example.com/novel")
    finally:
        crawler.close()

    assert response.status_code == 200
    assert call_count["value"] == 3


def test_request_blocks_when_robots_disallows(monkeypatch):
    settings = CrawlSettings(ignore_robots_txt=False)
    crawler = GenericNovelCrawler("https://example.com/novel", crawl_settings=settings)

    class FakeRobots:
        @staticmethod
        def can_fetch(user_agent, url):
            return False

    crawler._robots_parser = FakeRobots()
    crawler._robots_checked = True

    try:
        with pytest.raises(PermissionError):
            crawler._request("GET", "https://example.com/novel")
    finally:
        crawler.close()
