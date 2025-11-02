from __future__ import annotations

from pathlib import Path
from typing import Dict

import httpx
import pytest

from sagemtl.crawl.http import HTTPClient, HTTPClientConfig, RobotsDisallowed


def build_client(tmp_path: Path, handler) -> HTTPClient:
    transport = httpx.MockTransport(handler)
    config = HTTPClientConfig(cache_dir=tmp_path)
    return HTTPClient(config=config, transport=transport)


def test_retries_until_success(tmp_path):
    attempts = {"/data": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts[request.url.path] = attempts.get(request.url.path, 0) + 1
        if attempts[request.url.path] < 3:
            raise httpx.ReadTimeout("boom", request=request)
        return httpx.Response(200, text="ok")

    client = build_client(tmp_path, handler)
    assert client.get_text("https://example.com/data") == "ok"
    assert attempts["/data"] == 3


def test_robots_disallows_request(tmp_path):
    hits: Dict[str, int] = {"/robots.txt": 0, "/secret": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits[request.url.path] = hits.get(request.url.path, 0) + 1
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /secret",
            )
        if request.url.path == "/secret":
            pytest.fail("Request to disallowed path should not occur")
        return httpx.Response(200, text="ok")

    client = build_client(tmp_path, handler)
    with pytest.raises(RobotsDisallowed):
        client.get_text("https://example.com/secret")

    assert hits["/robots.txt"] == 1
    assert hits["/secret"] == 0


def test_cache_prevents_repeat_requests(tmp_path):
    calls = {"/cache-me": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls[request.url.path] = calls.get(request.url.path, 0) + 1
        if calls[request.url.path] > 1:
            pytest.fail("Second request should be served from cache")
        return httpx.Response(200, text="cached")

    client = build_client(tmp_path, handler)
    first = client.get_text("https://example.com/cache-me")
    second = client.get_text("https://example.com/cache-me")

    assert first == second == "cached"
    assert calls["/cache-me"] == 1

