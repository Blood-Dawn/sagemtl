"""Data models for the SageMTL manga module.

These dataclasses are intentionally dependency-light: importing this module must
never pull in torch, onnxruntime, paddle, opencv, transformers, or numpy. The
only reference to numpy is a type annotation guarded behind ``TYPE_CHECKING`` so
the novel path can import the manga models with zero heavy imports.

See ``MANGA_MODULE_BUILD_SPEC.md`` sections 2.3, 3, 10.1, and 12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    import numpy as np


# ---------------------------------------------------------------------------
# Stage-level models (pipeline contract, spec 2.3 / 3)
# ---------------------------------------------------------------------------


@dataclass
class TextRegion:
    """A single detected text region on a page.

    ``mask`` holds a per-pixel text mask (uint8) cropped to the page. It is kept
    as a runtime-only numpy array and is dropped when serializing to disk (see
    :meth:`to_dict`).
    """

    box: tuple[int, int, int, int]            # x1, y1, x2, y2
    polygon: list[tuple[int, int]] = field(default_factory=list)
    cls: str = "text_bubble"                  # bubble | text_bubble | text_free
    mask: Optional["np.ndarray"] = None       # per-pixel text mask, page-cropped
    source_text: str = ""
    target_text: str = ""
    lang: str = ""
    conf: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize without the numpy mask (image bytes live on disk)."""
        return {
            "box": list(self.box),
            "polygon": [list(point) for point in self.polygon],
            "cls": self.cls,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "lang": self.lang,
            "conf": self.conf,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextRegion":
        box = tuple(data.get("box", (0, 0, 0, 0)))  # type: ignore[assignment]
        polygon = [tuple(point) for point in data.get("polygon", [])]
        return cls(
            box=box,  # type: ignore[arg-type]
            polygon=polygon,  # type: ignore[arg-type]
            cls=data.get("cls", "text_bubble"),
            source_text=data.get("source_text", ""),
            target_text=data.get("target_text", ""),
            lang=data.get("lang", ""),
            conf=float(data.get("conf", 0.0)),
        )


@dataclass
class PageResult:
    """Result of running the pipeline on one page (spec 2.3)."""

    index: int
    regions: list[TextRegion] = field(default_factory=list)
    clean_image: bytes = b""        # page after inpaint
    rendered_image: bytes = b""     # page after typeset
    debug: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Persistence models (spec 10.1)
# ---------------------------------------------------------------------------


@dataclass
class MangaPage:
    """A single page within a chapter (persisted; image bytes stay on disk)."""

    index: int
    source_image_path: str = ""        # raw downloaded page
    clean_image_path: str = ""         # after inpaint
    rendered_image_path: str = ""      # after typeset
    regions: list[dict] = field(default_factory=list)  # serialized TextRegion
    status: str = "pending"            # pending|ocr|translated|typeset|done|error

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "source_image_path": self.source_image_path,
            "clean_image_path": self.clean_image_path,
            "rendered_image_path": self.rendered_image_path,
            "regions": list(self.regions),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MangaPage":
        return cls(
            index=int(data.get("index", 0)),
            source_image_path=data.get("source_image_path", ""),
            clean_image_path=data.get("clean_image_path", ""),
            rendered_image_path=data.get("rendered_image_path", ""),
            regions=list(data.get("regions", [])),
            status=data.get("status", "pending"),
        )


@dataclass
class MangaChapter:
    """An ordered set of pages (spec 10.1)."""

    chapter_id: str
    number: str = ""
    title: str = ""
    source_url: str = ""
    lang: str = ""
    pages: list[MangaPage] = field(default_factory=list)
    is_webtoon: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "number": self.number,
            "title": self.title,
            "source_url": self.source_url,
            "lang": self.lang,
            "pages": [page.to_dict() for page in self.pages],
            "is_webtoon": self.is_webtoon,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MangaChapter":
        pages = [MangaPage.from_dict(page) for page in data.get("pages", [])]
        return cls(
            chapter_id=data.get("chapter_id", ""),
            number=data.get("number", ""),
            title=data.get("title", ""),
            source_url=data.get("source_url", ""),
            lang=data.get("lang", ""),
            pages=pages,
            is_webtoon=bool(data.get("is_webtoon", False)),
        )


@dataclass
class MangaSeries:
    """A manga series in the library (spec 10.1)."""

    series_id: str                     # uuid
    title: str = ""
    source_url: str = ""
    source_name: str = ""              # e.g. 'mangadex'
    cover_path: str = ""
    lang: str = ""
    chapters: list[MangaChapter] = field(default_factory=list)
    title_locked: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "title": self.title,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "cover_path": self.cover_path,
            "lang": self.lang,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "title_locked": self.title_locked,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MangaSeries":
        chapters = [MangaChapter.from_dict(ch) for ch in data.get("chapters", [])]
        return cls(
            series_id=data.get("series_id", ""),
            title=data.get("title", ""),
            source_url=data.get("source_url", ""),
            source_name=data.get("source_name", ""),
            cover_path=data.get("cover_path", ""),
            lang=data.get("lang", ""),
            chapters=chapters,
            title_locked=bool(data.get("title_locked", False)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ---------------------------------------------------------------------------
# Configuration model (spec 12)
# ---------------------------------------------------------------------------


@dataclass
class MangaConfig:
    """User-facing manga configuration.

    Persisted through ``DesktopSettingsStore`` to ``~/.sagemtl/config.toml`` with
    a ``manga_`` prefix. API keys are never stored here; ``cloud_api_key_env``
    only names the environment variable that holds the key.
    """

    engine_mode: str = "hybrid"        # offline | hybrid | cloud
    target_lang: str = "en"
    source_lang: str = "auto"          # auto | ja | ko | zh
    # models
    detector_model: str = "ogkalu/comic-text-and-bubble-detector"
    ja_ocr_model: str = "kha-white/manga-ocr-base"
    cjk_ocr_engine: str = "paddleocr"  # paddleocr | easyocr
    ocr_vlm_model: str = "PaddlePaddle/PaddleOCR-VL"
    inpaint_model: str = "dreMaz/AnimeMangaInpainting"
    offline_mt_model: str = "haoranxu/X-ALMA-13B-Group6"
    # cloud
    cloud_provider: str = "anthropic"  # anthropic | google | openai | none
    cloud_model: str = "claude-sonnet-4-6"
    cloud_api_key_env: str = "ANTHROPIC_API_KEY"  # env var name only, never the key
    cost_ceiling_usd_per_chapter: float = 1.0
    # typeset
    font_path: str = "core/manga/fonts/ComicNeue-Bold.ttf"
    enable_vertical_cjk: bool = False
    # device
    device: str = "auto"               # auto | cpu | cuda
    # crawler sources (Suwayomi bridge -- user runs their own Mihon extensions)
    suwayomi_url: str = ""             # e.g. http://localhost:4567
    suwayomi_source_id: str = ""
