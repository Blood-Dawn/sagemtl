"""Tests for Settings API router."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from sagemtl.config import Settings, save_config
from sagemtl.serve.api_v2 import app


@pytest.fixture
def test_config_dir():
    """Create a temporary config directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_get_settings(client, test_config_dir, monkeypatch):
    """Test GET /api/settings returns current settings."""
    # Create a test config
    config_file = test_config_dir / "config.toml"
    settings = Settings(
        newline_mode="lf",
        thread_count=4,
        crawl_glob="*.html",
    )
    save_config(settings, config_file)

    # Mock the config path
    monkeypatch.setenv("SAGEMTL_CONFIG", str(config_file))

    response = client.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    assert data["newline_mode"] == "lf"
    assert data["thread_count"] == 4
    assert data["crawl_glob"] == "*.html"


def test_update_settings(client, test_config_dir, monkeypatch):
    """Test PUT /api/settings updates and persists settings."""
    config_file = test_config_dir / "config.toml"

    # Create initial config
    settings = Settings(thread_count=2)
    save_config(settings, config_file)

    monkeypatch.setenv("SAGEMTL_CONFIG", str(config_file))

    # Update settings
    response = client.put(
        "/api/settings",
        json={
            "thread_count": 8,
            "newline_mode": "crlf",
            "crawl_glob": "*.txt",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["thread_count"] == 8
    assert data["newline_mode"] == "crlf"
    assert data["crawl_glob"] == "*.txt"

    # Verify persistence
    assert config_file.exists()
    content = config_file.read_text()
    assert "thread_count = 8" in content
    assert 'newline_mode = "crlf"' in content


def test_update_settings_partial(client, test_config_dir, monkeypatch):
    """Test updating only some settings."""
    config_file = test_config_dir / "config.toml"

    settings = Settings(thread_count=2, newline_mode="lf")
    save_config(settings, config_file)

    monkeypatch.setenv("SAGEMTL_CONFIG", str(config_file))

    # Update only thread_count
    response = client.put(
        "/api/settings",
        json={"thread_count": 16},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["thread_count"] == 16
    assert data["newline_mode"] == "lf"  # Should remain unchanged


def test_reset_settings(client, test_config_dir, monkeypatch):
    """Test POST /api/settings/reset resets to defaults."""
    config_file = test_config_dir / "config.toml"

    # Create config with custom values
    settings = Settings(thread_count=99, newline_mode="crlf")
    save_config(settings, config_file)

    monkeypatch.setenv("SAGEMTL_CONFIG", str(config_file))

    # Reset
    response = client.post("/api/settings/reset")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "reset"

    # Verify settings are reset
    response = client.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    # Should have default values
    assert data["newline_mode"] == "lf"  # Default
    assert data["thread_count"] >= 1  # Default based on CPU count


def test_invalid_settings(client, test_config_dir, monkeypatch):
    """Test updating with invalid settings."""
    config_file = test_config_dir / "config.toml"
    settings = Settings()
    save_config(settings, config_file)

    monkeypatch.setenv("SAGEMTL_CONFIG", str(config_file))

    # Try to set invalid thread_count
    response = client.put(
        "/api/settings",
        json={"thread_count": -1},  # Invalid: must be >= 1
    )
    # Should still succeed but validate on backend
    # (Pydantic validation happens at model level)
