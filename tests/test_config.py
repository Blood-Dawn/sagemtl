from __future__ import annotations

from pathlib import Path

from sagemtl.config import (
    CONFIG_ENV_VAR,
    Settings,
    clear_config_cache,
    default_config_path,
    load_config,
    resolve_newline,
    save_config,
    update_config,
)


def test_default_config_location(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    path = default_config_path()
    assert path.name == "config.toml"
    assert path.parent.name == ".sagemtl"


def test_load_config_defaults(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.toml"
    monkeypatch.setenv(CONFIG_ENV_VAR, str(cfg))
    clear_config_cache()
    settings = load_config()
    assert settings.clean_input_path == "-"
    assert settings.clean_output_path is None
    assert settings.crawl_glob == "*.html"
    assert settings.thread_count >= 1
    assert resolve_newline(settings.newline_mode) == "\n"


def test_save_and_reload(tmp_path: Path):
    cfg_path = tmp_path / "conf.toml"
    settings = Settings(
        newline_mode="system",
        clean_input_path="input.txt",
        clean_output_path="out.txt",
        crawl_glob="**/*.html",
        crawl_outdir="crawl",
        crawl_jsonl=True,
        thread_count=12,
    )

    save_config(settings, cfg_path)
    clear_config_cache()
    loaded = load_config(cfg_path, use_cache=False)
    assert loaded == settings

    text = cfg_path.read_text(encoding="utf-8")
    assert 'clean_input_path = "input.txt"' in text
    assert "thread_count = 12" in text


def test_update_config(tmp_path: Path):
    cfg = tmp_path / "conf.toml"
    save_config(Settings(), cfg)
    clear_config_cache()

    new_settings = update_config({"thread_count": 5, "newline_mode": "crlf"}, cfg)
    assert new_settings.thread_count == 5
    assert new_settings.newline_mode == "crlf"

    clear_config_cache()
    reloaded = load_config(cfg, use_cache=False)
    assert reloaded.thread_count == 5
    assert reloaded.newline_mode == "crlf"


def test_invalid_config_is_sanitized(tmp_path: Path):
    cfg = tmp_path / "conf.toml"
    cfg.write_text('thread_count = -4\nnewline_mode = "bogus"\n', encoding="utf-8")
    clear_config_cache()
    settings = load_config(cfg, use_cache=False)
    assert settings.thread_count >= 1
    assert settings.newline_mode == "lf"


def test_save_config_respects_env_override(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "conf.toml"
    monkeypatch.setenv(CONFIG_ENV_VAR, str(cfg))
    clear_config_cache()
    save_config(Settings(clean_input_path="foo.txt"))
    data = cfg.read_text(encoding="utf-8")
    assert 'clean_input_path = "foo.txt"' in data
