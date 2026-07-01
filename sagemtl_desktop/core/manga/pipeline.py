"""Manga pipeline orchestrator.

``MangaPipeline`` chains the per-page stages (detect -> reading order -> OCR ->
translate -> inpaint -> typeset) into one callable the UI and CLI share. Importing
this module stays cheap: it imports only the light data models here, and every
stage module (and its heavy ML dependency) is imported lazily inside
``process_page``. Loaded models are cached on the instance and reused across pages
of a chapter.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 2.3.
"""

from __future__ import annotations

import io
import os
import time
from typing import TYPE_CHECKING, Callable, Optional

from .models import MangaConfig, PageResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sagemtl_desktop.core.glossary_manager import GlossaryManager

ProgressCb = Optional[Callable[[float], None]]
LogCb = Optional[Callable[[str], None]]


def _encode_png(rgb) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="PNG")
    return buffer.getvalue()


def _summarize_page(result: PageResult, *, max_chars: int = 400) -> str:
    """Build a short rolling-context summary from a page's translated regions.

    Quality peaks at one page of context (spec 6.1 / risk note), so this is just
    the previous page's translated lines, truncated.
    """

    lines = [r.target_text.strip() for r in result.regions if r.target_text.strip()]
    summary = " ".join(lines)
    return summary[:max_chars]


class MangaPipeline:
    """Orchestrates stages 1..5 for one page or chapter (spec 2.3)."""

    def __init__(self, config: MangaConfig, glossary: "GlossaryManager | None" = None) -> None:
        self.config = config
        self.glossary = glossary
        # Lazy, reused-across-pages model caches.
        self._detector = None
        self._ocr_engines: dict = {}
        self._translate_engine = None
        self._inpainter = None
        self._provider = None
        self._provider_built = False
        # Per-region result caches reused across pages of a chapter (and re-runs).
        self._ocr_cache: dict = {}
        self._translate_cache: dict = {}

    # -- lazy stage handles -------------------------------------------------

    def _get_detector(self):
        if self._detector is None:
            from . import detect

            self._detector = detect.Detector(device=self.config.device)
        return self._detector

    def _get_translate_engine(self):
        if self._translate_engine is None:
            from . import translate

            self._translate_engine = translate.build_engine(self.config)
        return self._translate_engine

    def _get_inpainter(self):
        if self._inpainter is None:
            from . import inpaint

            self._inpainter = inpaint.build_inpainter(self.config)  # None -> classical
        return self._inpainter

    def _get_provider(self, source_lang: str):
        if self._provider_built:
            return self._provider
        self._provider_built = True
        cfg = self.config
        if cfg.engine_mode == "offline" or cfg.cloud_provider == "none":
            self._provider = None
        elif not os.environ.get(cfg.cloud_api_key_env):
            self._provider = None  # no key -> fall back to offline
        else:
            from . import providers

            ceiling = cfg.cost_ceiling_usd_per_chapter
            self._provider = providers.build_provider(
                cfg.cloud_provider, cfg.cloud_model, cfg.cloud_api_key_env,
                source_lang=source_lang,
                cost_tracker=providers.CostTracker(ceiling) if ceiling else None,
            )
        return self._provider

    def _effective_lang(self, source_lang: Optional[str]) -> str:
        from .ocr import normalize_lang

        chosen = source_lang or self.config.source_lang or "auto"
        if chosen == "auto":
            return "auto"
        return normalize_lang(chosen) or "auto"

    # -- main entry points --------------------------------------------------

    def process_page(
        self,
        image: bytes,
        *,
        source_lang: Optional[str] = None,
        series_id: str = "",
        page_index: int = 0,
        rolling_summary: str = "",
        progress_cb: ProgressCb = None,
        log_cb: LogCb = None,
    ) -> PageResult:
        """Run stages 1..5 on one page image and return a :class:`PageResult`."""

        from . import detect, inpaint, ocr, reading_order, translate, webtoon

        def progress(pct: float) -> None:
            if progress_cb:
                progress_cb(pct)

        def log(message: str) -> None:
            if log_cb:
                log_cb(message)

        cfg = self.config
        eff_lang = self._effective_lang(source_lang)
        debug: dict = {"page_index": page_index, "lang": eff_lang, "timings": {}}

        rgb = detect.load_image_rgb(image)
        progress(5.0)

        # Stage 1 (+6): detection, tiled for tall webtoon strips
        t0 = time.perf_counter()
        is_strip = webtoon.is_strip(rgb.shape)
        if is_strip:
            regions, _mask = webtoon.tiled_detect(self._get_detector(), rgb)
        else:
            regions, _mask = self._get_detector().detect(rgb)
        text_regions = [r for r in regions if r.cls in detect.TEXT_CLASSES]
        debug["timings"]["detect"] = time.perf_counter() - t0
        debug["region_count"] = len(text_regions)
        debug["is_strip"] = is_strip
        log(f"[manga] page {page_index}: detected {len(text_regions)} text regions"
            f"{' (webtoon strip)' if is_strip else ''}")
        progress(25.0)

        # Stage 1b: reading order
        ordered = reading_order.sort(text_regions, source_lang=eff_lang)

        # Stage 2: OCR
        t0 = time.perf_counter()
        ocr.run(
            ordered, rgb, source_lang=eff_lang, engines=self._ocr_engines,
            config=cfg, cache=self._ocr_cache, log_cb=log_cb,
        )
        debug["timings"]["ocr"] = time.perf_counter() - t0
        progress(50.0)

        # Stage 3: translation
        t0 = time.perf_counter()
        provider = self._get_provider(eff_lang if eff_lang != "auto" else "ja")
        translate.run(
            ordered, page_png=image, source_lang=eff_lang, target_lang=cfg.target_lang,
            glossary=self.glossary, mode=cfg.engine_mode, rolling_summary=rolling_summary,
            series_id=series_id, config=cfg,
            offline_engine=self._get_translate_engine(), provider=provider,
            cache=self._translate_cache, log_cb=log_cb,
        )
        debug["timings"]["translate"] = time.perf_counter() - t0
        progress(70.0)

        # Stage 4: erase + inpaint
        t0 = time.perf_counter()
        clean = inpaint.run(rgb, regions, inpainter=self._get_inpainter())
        debug["timings"]["inpaint"] = time.perf_counter() - t0
        progress(85.0)

        # Stage 5: typeset
        t0 = time.perf_counter()
        from . import typeset

        rendered = typeset.render(clean, ordered, font_path=cfg.font_path, target_lang=cfg.target_lang)
        debug["timings"]["typeset"] = time.perf_counter() - t0
        progress(100.0)

        return PageResult(
            index=page_index,
            regions=ordered,
            clean_image=_encode_png(clean),
            rendered_image=_encode_png(rendered),
            debug=debug,
        )

    def process_chapter(
        self,
        pages: list[bytes],
        *,
        source_lang: Optional[str] = None,
        series_id: str = "",
        progress_cb: ProgressCb = None,
        log_cb: LogCb = None,
    ) -> list[PageResult]:
        """Run :meth:`process_page` across an ordered list of page images."""

        results: list[PageResult] = []
        total = max(1, len(pages))
        rolling = ""
        for index, page in enumerate(pages):
            result = self.process_page(
                page, source_lang=source_lang, series_id=series_id, page_index=index,
                rolling_summary=rolling, log_cb=log_cb,
            )
            results.append(result)
            rolling = _summarize_page(result)  # 1-page rolling context for the next page
            if progress_cb:
                progress_cb((index + 1) / total * 100.0)
        return results
