"""Central model registry, lazy download/caching, and device selection.

This module is import-safe: it never imports torch, huggingface_hub, onnxruntime,
or any other heavy dependency at module load time. Every heavy import lives inside
a function body so the novel path (and a plain ``import`` of this module) stays
cheap. Models are downloaded on demand into ``~/.sagemtl/models/`` and loaded
through :func:`load`, which caches one handle per key (lazy singletons).

See ``MANGA_MODULE_BUILD_SPEC.md`` section 8.3 and Appendix A. Only permissive
(Apache-2.0 / MIT) weights are registered here; non-commercial models are
deliberately excluded and may only be added later as user-supplied engines behind
an explicit "research mode" guard (spec section 16, Phase 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

__all__ = [
    "ModelSpec",
    "MODEL_REGISTRY",
    "get_spec",
    "list_models",
    "models_cache_dir",
    "select_device",
    "ensure",
    "load",
    "is_loaded",
    "clear_loaded_cache",
    "set_research_mode",
    "is_research_mode",
    "is_commercial_ok",
    "assert_repo_allowed",
    "NON_COMMERCIAL_REPOS",
    "NonCommercialModelError",
]


class NonCommercialModelError(PermissionError):
    """Raised when a non-commercial model is used without research mode enabled."""


# Known non-commercial weights the project must never bundle/auto-load (spec 16).
# They may only be used as user-supplied engines after enabling research mode.
NON_COMMERCIAL_REPOS = frozenset({
    "ragavsachdeva/magi",
    "ragavsachdeva/magiv2",
    "facebook/nllb-200-distilled-600M",
    "facebook/nllb-200-1.3B",
    "OpenLLM-Korea/VARCO-VISION-2.0-1.7B-OCR",
    "Unbabel/TowerInstruct-7B-v0.2",
    "black-forest-labs/FLUX.1-Fill-dev",
})

_RESEARCH_MODE = False


def set_research_mode(enabled: bool) -> None:
    """Enable/disable loading non-commercial models (user opt-in only)."""

    global _RESEARCH_MODE
    _RESEARCH_MODE = bool(enabled)


def is_research_mode() -> bool:
    return _RESEARCH_MODE


def is_commercial_ok(spec: "ModelSpec") -> bool:
    """True if a spec is safe to ship (permissive license, not on the NC list)."""

    return bool(spec.commercial_ok) and spec.repo_id not in NON_COMMERCIAL_REPOS


def _check_license(spec: "ModelSpec") -> None:
    if not is_commercial_ok(spec) and not _RESEARCH_MODE:
        raise NonCommercialModelError(
            f"Model {spec.key!r} ({spec.repo_id}) is non-commercial and will not be "
            f"loaded. Enable research mode (set_research_mode(True)) to use it."
        )


def assert_repo_allowed(name: str) -> str:
    """Enforce the NC guard for a registry key OR a raw repo id; return the repo id.

    Use this on any code path that downloads/loads a model outside ``ensure``/``load``
    (e.g. handing a repo id straight to ``transformers.pipeline``).
    """

    if name in MODEL_REGISTRY:
        spec = MODEL_REGISTRY[name]
        _check_license(spec)
        return spec.repo_id
    if name in NON_COMMERCIAL_REPOS and not _RESEARCH_MODE:
        raise NonCommercialModelError(
            f"Model {name!r} is non-commercial and will not be loaded. "
            f"Enable research mode (set_research_mode(True)) to use it."
        )
    return name


@dataclass(frozen=True)
class ModelSpec:
    """Static metadata describing a downloadable model."""

    key: str
    repo_id: str
    kind: str               # detector | segmenter | ocr | ocr_vlm | inpaint | mt | panel
    license: str            # SPDX-style identifier, e.g. "Apache-2.0" or "MIT"
    commercial_ok: bool = True
    files: tuple[str, ...] = field(default_factory=tuple)  # optional subset to fetch
    revision: Optional[str] = None
    notes: str = ""


# Permissive defaults only (spec Appendix A / section 16). Keys are stable logical
# names; the concrete repo can be swapped via MangaConfig without touching callers.
MODEL_REGISTRY: dict[str, ModelSpec] = {
    # Detection
    "detector": ModelSpec(
        key="detector",
        repo_id="ogkalu/comic-text-and-bubble-detector",
        kind="detector",
        license="Apache-2.0",
        files=("detector.onnx", "config.json", "preprocessor_config.json"),
        notes="RT-DETR-v2 bubble + text detector (ONNX path; skips safetensors).",
    ),
    "segmenter": ModelSpec(
        key="segmenter",
        repo_id="ogkalu/comic-text-segmenter-yolov8m",
        kind="segmenter",
        license="Apache-2.0",
        notes="Tighter glyph segmentation mask for inpainting.",
    ),
    "bubble_detector": ModelSpec(
        key="bubble_detector",
        repo_id="ogkalu/comic-speech-bubble-detector-yolov8m",
        kind="detector",
        license="Apache-2.0",
        notes="Webtoon-robust bubble boxes.",
    ),
    "panel_detector": ModelSpec(
        key="panel_detector",
        repo_id="mosesb/best-comic-panel-detection",
        kind="panel",
        license="Apache-2.0",
        notes="Optional panel detector for reading order.",
    ),
    # OCR
    "ocr_ja": ModelSpec(
        key="ocr_ja",
        repo_id="kha-white/manga-ocr-base",
        kind="ocr",
        license="Apache-2.0",
        notes="Japanese manga OCR (vertical + horizontal, furigana).",
    ),
    "ocr_vlm": ModelSpec(
        key="ocr_vlm",
        repo_id="PaddlePaddle/PaddleOCR-VL",
        kind="ocr_vlm",
        license="Apache-2.0",
        notes="Sub-1B vision-LLM OCR escalation, 109 languages.",
    ),
    "ocr_vlm_qwen": ModelSpec(
        key="ocr_vlm_qwen",
        repo_id="Qwen/Qwen3-VL-8B-Instruct",
        kind="ocr_vlm",
        license="Apache-2.0",
        notes="Robust OCR on stylized text.",
    ),
    "ocr_vlm_dots": ModelSpec(
        key="ocr_vlm_dots",
        repo_id="rednote-hilab/dots.mocr",
        kind="ocr_vlm",
        license="MIT",
        notes="Layout + reading order + recognition in one VLM.",
    ),
    # Inpaint
    "inpaint_lama": ModelSpec(
        key="inpaint_lama",
        repo_id="dreMaz/AnimeMangaInpainting",
        kind="inpaint",
        license="MIT",
        notes="Manga-finetuned LaMa, default neural inpainter.",
    ),
    "inpaint_aot": ModelSpec(
        key="inpaint_aot",
        repo_id="mayocream/aot-inpainting",
        kind="inpaint",
        license="Apache-2.0",
        notes="AOT-GAN manga-trained ONNX fallback.",
    ),
    # Offline machine translation
    "mt_xalma": ModelSpec(
        key="mt_xalma",
        repo_id="haoranxu/X-ALMA-13B-Group6",
        kind="mt",
        license="MIT",
        notes="All-CJK offline translator.",
    ),
    "mt_sugoi": ModelSpec(
        key="mt_sugoi",
        repo_id="sugoitoolkit/Sugoi-14B-Ultra-GGUF",
        kind="mt",
        license="Apache-2.0",
        notes="Best offline JA->EN, GGUF for llama.cpp.",
    ),
    "mt_qwen14b": ModelSpec(
        key="mt_qwen14b",
        repo_id="Qwen/Qwen3-14B",
        kind="mt",
        license="Apache-2.0",
        notes="Strong ja/ko/zh->en with glossary prompting.",
    ),
    "mt_m2m100": ModelSpec(
        key="mt_m2m100",
        repo_id="facebook/m2m100_1.2B",
        kind="mt",
        license="MIT",
        notes="Tiny CPU last resort, direct CJK->EN.",
    ),
}


# One cached handle per model key (lazy singletons populated by load()).
_LOADED: dict[str, Any] = {}


def get_spec(key: str) -> ModelSpec:
    """Return the :class:`ModelSpec` for ``key`` or raise ``KeyError``."""

    try:
        return MODEL_REGISTRY[key]
    except KeyError:
        known = ", ".join(sorted(MODEL_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown manga model key {key!r}. Known keys: {known}") from None


def list_models() -> list[ModelSpec]:
    """Return all registered model specs."""

    return list(MODEL_REGISTRY.values())


def models_cache_dir() -> Path:
    """Return the local model cache directory (``~/.sagemtl/models``).

    This only computes the path; it does not create the directory or download
    anything. :func:`ensure` is responsible for creating it on first use.
    """

    return Path.home() / ".sagemtl" / "models"


def select_device(preference: str = "auto") -> str:
    """Resolve a device string to ``"cpu"`` or ``"cuda"``.

    ``preference`` may be ``auto``, ``cpu``, or ``cuda``. The torch import is
    lazy and failure-tolerant: if torch is unavailable or CUDA is not present,
    this falls back to ``"cpu"``.
    """

    pref = (preference or "auto").strip().lower()
    if pref == "cpu":
        return "cpu"

    cuda_available = False
    try:
        import torch  # local import keeps module import cheap

        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        cuda_available = False

    if pref == "cuda":
        return "cuda" if cuda_available else "cpu"
    # auto
    return "cuda" if cuda_available else "cpu"


def ensure(key: str, *, cache_dir: Optional[Path] = None, revision: Optional[str] = None) -> Path:
    """Download (if needed) the model for ``key`` and return its local path.

    Uses ``huggingface_hub.snapshot_download`` into ``~/.sagemtl/models``. The
    huggingface_hub import is lazy. This performs network I/O and must not be
    called at import time. Raises ``KeyError`` for unknown keys and
    ``RuntimeError`` if huggingface_hub is not installed.
    """

    spec = get_spec(key)
    _check_license(spec)
    target_dir = Path(cache_dir) if cache_dir is not None else models_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "huggingface_hub is required to download manga models. Install the "
            "manga extras: pip install -r requirements-manga.txt"
        ) from exc

    allow_patterns = list(spec.files) if spec.files else None
    local_path = snapshot_download(
        repo_id=spec.repo_id,
        revision=revision or spec.revision,
        cache_dir=str(target_dir),
        allow_patterns=allow_patterns,
    )
    return Path(local_path)


def load(key: str, loader: Optional[Callable[[ModelSpec], Any]] = None) -> Any:
    """Return a cached model handle, building it once via ``loader`` if needed.

    The first call for a key invokes ``loader(spec)`` and caches the result; later
    calls return the same handle without re-invoking the loader (lazy singleton).
    Stage modules supply their own ``loader`` (which typically calls :func:`ensure`
    and then loads the weights). Raises ``KeyError`` for unknown keys and
    ``RuntimeError`` if the model is not cached and no loader is provided.
    """

    spec = get_spec(key)
    _check_license(spec)
    if key in _LOADED:
        return _LOADED[key]
    if loader is None:
        raise RuntimeError(
            f"Model {key!r} is not loaded yet; pass a loader callable to load() "
            "so the registry can build and cache it."
        )
    handle = loader(spec)
    _LOADED[key] = handle
    return handle


def is_loaded(key: str) -> bool:
    """Return True if a handle for ``key`` is currently cached."""

    return key in _LOADED


def clear_loaded_cache(key: Optional[str] = None) -> None:
    """Drop one or all cached model handles (used by tests and on reconfigure)."""

    if key is None:
        _LOADED.clear()
    else:
        _LOADED.pop(key, None)
