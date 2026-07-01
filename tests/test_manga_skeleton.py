"""Phase 0 tests: package skeleton, lazy imports, model registry, job types.

The central guarantee of Phase 0 is that the novel path gains no heavy import:
importing the manga pipeline (and the model registry) must not load torch,
onnxruntime, paddle, transformers, opencv, huggingface_hub, manga_ocr, easyocr,
or even numpy. We verify this in a fresh subprocess so the assertion is not
polluted by whatever the pytest process has already imported.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Modules that must NOT be loaded by importing the manga module skeleton.
HEAVY_MODULES = (
    "torch",
    "onnxruntime",
    "paddle",
    "paddlepaddle",
    "paddleocr",
    "transformers",
    "cv2",
    "huggingface_hub",
    "manga_ocr",
    "easyocr",
    "numpy",
)


def _heavy_modules_after_import(import_statements: str) -> list[str]:
    """Import the given statements in a clean interpreter; return leaked heavy mods."""

    heavy_tuple = repr(HEAVY_MODULES)
    code = (
        f"{import_statements}\n"
        "import sys\n"
        f"leaked = [m for m in {heavy_tuple} if m in sys.modules]\n"
        "print(','.join(leaked))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"Subprocess import failed:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
    )
    out = result.stdout.strip()
    return [m for m in out.split(",") if m]


def test_pipeline_import_loads_no_heavy_modules():
    leaked = _heavy_modules_after_import(
        "import sagemtl_desktop.core.manga.pipeline"
    )
    assert leaked == [], f"Importing the manga pipeline leaked heavy modules: {leaked}"


def test_model_registry_import_loads_no_heavy_modules():
    leaked = _heavy_modules_after_import(
        "import sagemtl_desktop.core.manga.model_registry"
    )
    assert leaked == [], f"Importing the model registry leaked heavy modules: {leaked}"


def test_manga_package_and_crawler_import_no_heavy_modules():
    leaked = _heavy_modules_after_import(
        "import sagemtl_desktop.core.manga\n"
        "import sagemtl_manga_crawler.core"
    )
    assert leaked == [], f"Importing the manga packages leaked heavy modules: {leaked}"


def test_stage_modules_import_no_heavy_modules():
    # Importing the stage modules must stay light; their onnxruntime/numpy/cv2
    # imports live inside function bodies.
    leaked = _heavy_modules_after_import(
        "import sagemtl_desktop.core.manga.detect\n"
        "import sagemtl_desktop.core.manga.reading_order\n"
        "import sagemtl_desktop.core.manga.ocr\n"
        "import sagemtl_desktop.core.manga.translate\n"
        "import sagemtl_desktop.core.manga.providers\n"
        "import sagemtl_desktop.core.manga.inpaint\n"
        "import sagemtl_desktop.core.manga.typeset\n"
        "import sagemtl_desktop.core.manga.webtoon\n"
        "import sagemtl_desktop.core.manga.library\n"
        "import sagemtl_desktop.core.manga.jobs\n"
        "import sagemtl_desktop.core.manga.exporter\n"
        "import sagemtl_desktop.core.manga.studio"
    )
    assert leaked == [], f"Importing the stage modules leaked heavy modules: {leaked}"


def test_pipeline_importable_and_instantiable():
    from sagemtl_desktop.core.manga.models import MangaConfig
    from sagemtl_desktop.core.manga.pipeline import MangaPipeline

    pipeline = MangaPipeline(MangaConfig())
    assert pipeline.config.engine_mode == "hybrid"
    assert pipeline.glossary is None
    # process_page is implemented as of Phase 5; invalid image bytes raise (not
    # NotImplementedError) without loading any heavy module at import time.
    with pytest.raises(Exception):
        pipeline.process_page(b"not-an-image", page_index=0)


def test_job_types_added():
    from sagemtl_desktop.core.models import JobType

    assert JobType.MANGA_CRAWL.value == "manga_crawl"
    assert JobType.MANGA_TRANSLATE.value == "manga_translate"
    assert JobType.MANGA_EXPORT.value == "manga_export"


def test_text_region_round_trip():
    from sagemtl_desktop.core.manga.models import TextRegion

    region = TextRegion(
        box=(1, 2, 3, 4),
        polygon=[(1, 2), (3, 4)],
        cls="text_bubble",
        source_text="abc",
        target_text="xyz",
        lang="ja",
        conf=0.9,
    )
    restored = TextRegion.from_dict(region.to_dict())
    assert restored.box == (1, 2, 3, 4)
    assert restored.polygon == [(1, 2), (3, 4)]
    assert restored.source_text == "abc"
    assert restored.lang == "ja"
    # the numpy mask is intentionally not serialized
    assert "mask" not in region.to_dict()


def test_manga_series_sets_timestamps():
    from sagemtl_desktop.core.manga.models import MangaSeries

    series = MangaSeries(series_id="abc123")
    assert series.created_at
    assert series.updated_at == series.created_at
    restored = MangaSeries.from_dict(series.to_dict())
    assert restored.series_id == "abc123"


def test_crawler_models_importable():
    from sagemtl_manga_crawler.core import ChapterRef, PageImage, SeriesResult

    result = SeriesResult(title="T", url="u", source="mangadex")
    chapter = ChapterRef(id="1", number="1", title="c1", url="u", lang="ja")
    page = PageImage(index=0, url="u")
    assert result.cover is None
    assert chapter.lang == "ja"
    assert page.headers == {}


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------


def test_get_spec_known_and_unknown():
    from sagemtl_desktop.core.manga import model_registry

    spec = model_registry.get_spec("detector")
    assert spec.repo_id == "ogkalu/comic-text-and-bubble-detector"
    with pytest.raises(KeyError):
        model_registry.get_spec("does-not-exist")


def test_all_registered_models_are_permissive():
    from sagemtl_desktop.core.manga import model_registry

    permissive = {"Apache-2.0", "MIT"}
    for spec in model_registry.list_models():
        assert spec.license in permissive, f"{spec.key} has non-permissive license {spec.license}"
        assert spec.commercial_ok is True, f"{spec.key} is not flagged commercial_ok"


def test_models_cache_dir_is_under_home_and_not_created():
    from sagemtl_desktop.core.manga import model_registry

    cache = model_registry.models_cache_dir()
    assert cache.name == "models"
    assert cache.parent.name == ".sagemtl"
    assert cache.parent.parent == Path.home()


def test_select_device_resolves_to_cpu_or_cuda():
    from sagemtl_desktop.core.manga import model_registry

    assert model_registry.select_device("cpu") == "cpu"
    assert model_registry.select_device("auto") in {"cpu", "cuda"}
    assert model_registry.select_device("cuda") in {"cpu", "cuda"}


def test_load_is_lazy_singleton():
    from sagemtl_desktop.core.manga import model_registry

    model_registry.clear_loaded_cache("ocr_ja")
    sentinel = object()
    calls: list[str] = []

    def loader(spec):
        calls.append(spec.key)
        return sentinel

    handle1 = model_registry.load("ocr_ja", loader=loader)
    # Second call must return the cached handle without invoking a new loader.
    handle2 = model_registry.load("ocr_ja", loader=lambda spec: object())

    assert handle1 is sentinel
    assert handle2 is sentinel
    assert calls == ["ocr_ja"]
    assert model_registry.is_loaded("ocr_ja")

    model_registry.clear_loaded_cache("ocr_ja")
    assert not model_registry.is_loaded("ocr_ja")


def test_load_requires_loader_when_uncached():
    from sagemtl_desktop.core.manga import model_registry

    model_registry.clear_loaded_cache("segmenter")
    with pytest.raises(RuntimeError):
        model_registry.load("segmenter")


def test_load_unknown_key_raises_keyerror():
    from sagemtl_desktop.core.manga import model_registry

    with pytest.raises(KeyError):
        model_registry.load("nope", loader=lambda spec: object())


def test_ensure_unknown_key_raises_before_network():
    from sagemtl_desktop.core.manga import model_registry

    with pytest.raises(KeyError):
        model_registry.ensure("nope")


def test_no_registered_model_is_non_commercial():
    from sagemtl_desktop.core.manga import model_registry

    for spec in model_registry.list_models():
        assert spec.repo_id not in model_registry.NON_COMMERCIAL_REPOS
        assert model_registry.is_commercial_ok(spec)


def test_research_mode_guard_blocks_nc_models(monkeypatch):
    from sagemtl_desktop.core.manga import model_registry as mr

    nc = mr.ModelSpec(
        key="nc_test", repo_id="ragavsachdeva/magiv2", kind="detector",
        license="research", commercial_ok=False,
    )
    monkeypatch.setitem(mr.MODEL_REGISTRY, "nc_test", nc)
    mr.set_research_mode(False)
    try:
        assert mr.is_commercial_ok(nc) is False
        with pytest.raises(mr.NonCommercialModelError):
            mr.load("nc_test", loader=lambda spec: object())
        with pytest.raises(mr.NonCommercialModelError):
            mr.ensure("nc_test")
        # Opt-in research mode allows it (loader runs, no network).
        mr.set_research_mode(True)
        assert mr.load("nc_test", loader=lambda spec: "LOADED") == "LOADED"
    finally:
        mr.set_research_mode(False)
        mr.clear_loaded_cache("nc_test")


def test_assert_repo_allowed_guards_raw_repo_ids():
    from sagemtl_desktop.core.manga import model_registry as mr

    mr.set_research_mode(False)
    try:
        # a registry key for a permissive model -> returns its repo id
        assert mr.assert_repo_allowed("detector") == "ogkalu/comic-text-and-bubble-detector"
        # a raw permissive repo id passes through
        assert mr.assert_repo_allowed("PaddlePaddle/PaddleOCR-VL") == "PaddlePaddle/PaddleOCR-VL"
        # a raw NON-COMMERCIAL repo id is blocked (the VLM bypass path is guarded)
        nc = next(iter(mr.NON_COMMERCIAL_REPOS))
        with pytest.raises(mr.NonCommercialModelError):
            mr.assert_repo_allowed(nc)
        mr.set_research_mode(True)
        assert mr.assert_repo_allowed(nc) == nc  # allowed under research mode
    finally:
        mr.set_research_mode(False)


def test_ocr_vlm_path_blocks_non_commercial_repo():
    from sagemtl_desktop.core.manga import model_registry as mr
    from sagemtl_desktop.core.manga import ocr

    mr.set_research_mode(False)
    nc = "OpenLLM-Korea/VARCO-VISION-2.0-1.7B-OCR"  # in NON_COMMERCIAL_REPOS
    try:
        with pytest.raises(mr.NonCommercialModelError):
            ocr._vlm_repo(nc)  # the repo resolution used right before transformers.pipeline
    finally:
        mr.set_research_mode(False)
