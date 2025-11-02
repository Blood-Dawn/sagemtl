from __future__ import annotations

from fastapi.testclient import TestClient

from sagemtl.serve.api import app


client = TestClient(app)


def test_clean_endpoint_returns_meta():
    response = client.post("/clean", json={"text": "“Hello”"})
    assert response.status_code == 200
    data = response.json()
    assert data["text"].startswith('"Hello"')
    assert "length" in data["meta"]


def test_crawl_endpoint_inline_html():
    payload = {
        "html": "<html><body><article><p>Hello</p></article></body></html>",
        "options": {"ensure_trailing_lf": False},
    }
    response = client.post("/crawl", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["blocks"][0]["text"].startswith("Hello")


def test_translate_endpoint_creates_job():
    response = client.post("/translate", json={"text": "hi"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert "id" in payload
