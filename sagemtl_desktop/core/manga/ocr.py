"""Stage 2: routed OCR.

Recognizes the source text inside each detected region, routed by language:

    Japanese  -> manga-ocr (kha-white/manga-ocr-base), native multi-line bubbles.
    Korean    -> PaddleOCR PP-OCRv5 (lang='korean').
    Chinese   -> PaddleOCR PP-OCRv5 (lang='ch').

Because Stage 1 already localized the regions, Stage 2 does recognition on each
crop. PaddleOCR still runs its own line detector internally, so crops are padded
and upscaled first (small/low-res crops otherwise yield nothing). Low-confidence,
empty, or free-floating (SFX) regions can be escalated to a vision-LLM
(PaddleOCR-VL) when one is available; the escalation logic is always active, the
concrete VLM engine is optional and degrades to a no-op if its deps are missing.

Script detection mirrors the Unicode ranges in ``translator.detect_language`` but
prioritizes kana/Hangul so Japanese (kanji + kana) is not misread as Chinese.

All heavy imports (manga_ocr, paddleocr, transformers, numpy, cv2, PIL) are lazy
and live inside method bodies. See ``MANGA_MODULE_BUILD_SPEC.md`` section 5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from .models import TextRegion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

__all__ = [
    "run",
    "detect_script",
    "normalize_lang",
    "OcrResult",
    "OcrEngine",
    "MangaOcrEngine",
    "PaddleOcrEngine",
    "EasyOcrEngine",
    "PaddleVlmEngine",
    "build_engine",
    "DEFAULT_CONF_THRESHOLD",
]

LogCb = Optional[Callable[[str], None]]

# Confidence below which an engine result is escalated (engines that report it).
DEFAULT_CONF_THRESHOLD = 0.6
_NO_CONF = -1.0  # sentinel: engine does not report a confidence score
_MIN_REC_SIDE = 64
_CROP_PAD = 12

# Mirror of translator.detect_language ranges (kana/Hangul prioritized here).
_RE_KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_RE_HANGUL = re.compile(r"[\uac00-\ud7af]")
_RE_HAN = re.compile(r"[\u4e00-\u9fff]")


def normalize_lang(lang: str) -> str:
    """Normalize a language tag to one of ja|ko|zh|en (or '' for unknown)."""

    value = (lang or "").strip().lower()
    if not value:
        return ""
    if value.startswith(("ja", "jp")):
        return "ja"
    if value.startswith(("ko", "kr")):
        return "ko"
    if value.startswith(("zh", "cn", "ch")):
        return "zh"
    if value.startswith("en"):
        return "en"
    return value


def detect_script(text: str) -> str:
    """Return 'ja'/'ko'/'zh'/'en' (or '' if empty) from recognized text.

    Mirrors ``translator.detect_language`` (same Unicode ranges and 0.2 ratio),
    but checks Hangul then kana then Han so Japanese is not classified as Chinese.
    """

    sample = text[:500]
    total = len(sample.strip())
    if total == 0:
        return ""
    hangul = len(_RE_HANGUL.findall(sample))
    kana = len(_RE_KANA.findall(sample))
    han = len(_RE_HAN.findall(sample))
    threshold = 0.2
    if hangul / total > threshold:
        return "ko"
    if kana / total > threshold:
        return "ja"
    if han / total > threshold:
        return "zh"
    # Sparse fallback: any presence still indicates a script.
    if hangul:
        return "ko"
    if kana:
        return "ja"
    if han:
        return "zh"
    return "en"


@dataclass
class OcrResult:
    text: str
    conf: float           # _NO_CONF if the engine does not report confidence
    engine: str


class OcrEngine:
    """Base recognition engine. ``recognize`` takes an RGB HxWx3 crop."""

    name = "base"

    def recognize(self, crop_rgb: "np.ndarray") -> OcrResult:  # pragma: no cover - abstract
        raise NotImplementedError


def _prepare_crop(crop_rgb: "np.ndarray", min_side: int = _MIN_REC_SIDE, pad: int = _CROP_PAD) -> "np.ndarray":
    """Upscale small crops and add a white margin so a line detector can work."""

    import cv2

    height, width = crop_rgb.shape[:2]
    shortest = max(1, min(height, width))
    scale = max(1.0, min_side / shortest)
    if scale > 1.0:
        crop_rgb = cv2.resize(
            crop_rgb, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC
        )
    return cv2.copyMakeBorder(
        crop_rgb, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255)
    )


class MangaOcrEngine(OcrEngine):
    """Japanese OCR via manga-ocr (recognition-only, multi-line aware)."""

    name = "manga-ocr"

    def __init__(self) -> None:
        self._mocr = None

    def _ensure(self):
        if self._mocr is None:
            from manga_ocr import MangaOcr

            self._mocr = MangaOcr()
        return self._mocr

    def recognize(self, crop_rgb: "np.ndarray") -> OcrResult:
        from PIL import Image

        text = self._ensure()(Image.fromarray(crop_rgb)).strip()
        return OcrResult(text=text, conf=_NO_CONF, engine=self.name)


def _parse_paddle(result) -> tuple[list[str], list[float]]:
    """Extract (texts, scores) from a PaddleOCR 3.x or legacy result."""

    texts: list[str] = []
    scores: list[float] = []
    for item in result or []:
        getter = item.get if hasattr(item, "get") else None
        if getter is not None:
            recs = getter("rec_texts") or getter("rec_text") or []
            confs = getter("rec_scores") or getter("rec_score") or []
            if isinstance(recs, str):
                recs = [recs]
            if isinstance(confs, (int, float)):
                confs = [confs]
            texts.extend(str(t) for t in recs)
            scores.extend(float(c) for c in confs)
        elif isinstance(item, (list, tuple)):
            for line in item:
                try:
                    texts.append(str(line[1][0]))
                    scores.append(float(line[1][1]))
                except (IndexError, TypeError, ValueError):
                    continue
    return texts, scores


class PaddleOcrEngine(OcrEngine):
    """Korean/Chinese OCR via PaddleOCR PP-OCRv5 (recognition over padded crops)."""

    name = "paddleocr"
    _PADDLE_LANG = {"ko": "korean", "zh": "ch"}

    def __init__(self, lang: str) -> None:
        self.lang = normalize_lang(lang) or lang
        self._paddle_lang = self._PADDLE_LANG.get(self.lang, self.lang)
        self._ocr = None

    def _ensure(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            # enable_mkldnn=False avoids a oneDNN/PIR crash in paddlepaddle 3.x on
            # some CPUs; it is a no-op on GPU.
            self._ocr = PaddleOCR(lang=self._paddle_lang, enable_mkldnn=False)
        return self._ocr

    def recognize(self, crop_rgb: "np.ndarray") -> OcrResult:
        import numpy as np

        prepared = _prepare_crop(crop_rgb)
        result = self._ensure().predict(prepared[:, :, ::-1])  # paddle expects BGR
        texts, scores = _parse_paddle(result)
        text = " ".join(t.strip() for t in texts if t.strip()).strip()
        conf = float(np.mean(scores)) if scores else 0.0
        return OcrResult(text=text, conf=conf, engine=self.name)


class EasyOcrEngine(OcrEngine):
    """Optional Korean/Chinese OCR via EasyOCR (lighter accuracy, simple install)."""

    name = "easyocr"
    _EASY_LANG = {"ko": "ko", "zh": "ch_sim"}

    def __init__(self, lang: str) -> None:
        self.lang = normalize_lang(lang) or lang
        self._reader = None

    def _ensure(self):
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader([self._EASY_LANG.get(self.lang, self.lang)])
        return self._reader

    def recognize(self, crop_rgb: "np.ndarray") -> OcrResult:
        import numpy as np

        prepared = _prepare_crop(crop_rgb)
        rows = self._ensure().readtext(prepared)
        texts = [str(r[1]) for r in rows]
        scores = [float(r[2]) for r in rows]
        text = " ".join(t.strip() for t in texts if t.strip()).strip()
        conf = float(np.mean(scores)) if scores else 0.0
        return OcrResult(text=text, conf=conf, engine=self.name)


class PaddleVlmEngine(OcrEngine):
    """Vision-LLM OCR escalation (PaddleOCR-VL). Best-effort, optional.

    Heavy and not enabled by default; ``recognize`` degrades to an empty result if
    the model/deps are unavailable, so escalation never crashes the pipeline.
    """

    name = "paddleocr-vl"

    def __init__(self, model_key: str = "ocr_vlm", device: str = "auto") -> None:
        self.model_key = model_key
        self.device = device
        self._pipe = None

    def _ensure(self):
        if self._pipe is None:
            from transformers import pipeline

            self._pipe = pipeline("image-to-text", model=_vlm_repo(self.model_key))
        return self._pipe

    def recognize(self, crop_rgb: "np.ndarray") -> OcrResult:
        try:
            from PIL import Image

            out = self._ensure()(Image.fromarray(crop_rgb))
            text = ""
            if out:
                first = out[0]
                text = str(first.get("generated_text", "") if hasattr(first, "get") else first)
            return OcrResult(text=text.strip(), conf=_NO_CONF, engine=self.name)
        except Exception:
            return OcrResult(text="", conf=_NO_CONF, engine=self.name)


def _vlm_repo(model_key: str) -> str:
    from . import model_registry

    # Enforce the non-commercial guard here too: this path hands the repo straight
    # to transformers.pipeline (which downloads it), bypassing ensure()/load().
    return model_registry.assert_repo_allowed(model_key)


def build_engine(lang: str, config=None) -> OcrEngine:
    """Construct the primary OCR engine for a normalized language."""

    norm = normalize_lang(lang)
    if norm == "ja":
        return MangaOcrEngine()
    cjk_engine = getattr(config, "cjk_ocr_engine", "paddleocr") if config else "paddleocr"
    if cjk_engine == "easyocr":
        return EasyOcrEngine(norm or lang)
    return PaddleOcrEngine(norm or lang)


def _resolve_lang(region: TextRegion, source_lang: str) -> str:
    if region.lang:
        return normalize_lang(region.lang) or "ja"
    norm_source = normalize_lang(source_lang)
    if norm_source and source_lang != "auto":
        return norm_source
    # 'auto' with no per-region language: default to Japanese. In the full app the
    # crawler supplies the chapter language, so this default is rarely hit.
    return "ja"


def _crop(page_image: "np.ndarray", box: tuple[int, int, int, int]) -> "Optional[np.ndarray]":
    height, width = page_image.shape[:2]
    x1 = max(0, min(int(box[0]), width))
    y1 = max(0, min(int(box[1]), height))
    x2 = max(0, min(int(box[2]), width))
    y2 = max(0, min(int(box[3]), height))
    if x2 <= x1 or y2 <= y1:
        return None
    return page_image[y1:y2, x1:x2]


def _should_escalate(region: TextRegion, text: str, conf: float, threshold: float) -> bool:
    if not text.strip():
        return True
    if region.cls == "text_free":  # free / SFX text: hard for specialized OCR
        return True
    if conf != _NO_CONF and 0.0 <= conf < threshold:
        return True
    return False


def run(
    regions: Sequence[TextRegion],
    page_image: "np.ndarray",
    source_lang: str = "auto",
    escalate: bool = True,
    *,
    config=None,
    engines: Optional[dict] = None,
    vlm: Optional[OcrEngine] = None,
    conf_threshold: float = DEFAULT_CONF_THRESHOLD,
    cache: Optional[dict] = None,
    log_cb: LogCb = None,
) -> list[TextRegion]:
    """Fill ``source_text`` (and ``lang``/``conf``) for each region.

    ``engines`` is an optional injection/reuse dict keyed by normalized language
    ('ja'/'ko'/'zh') plus 'vlm'; it lets callers reuse loaded models across pages
    and lets tests inject fakes. ``cache`` (optional) is a per-region result cache
    keyed by language + crop content hash, so re-running a page does no OCR work.
    Returns the same region list.
    """

    import hashlib

    region_list = list(regions)
    engine_cache: dict = engines if engines is not None else {}

    for region in region_list:
        lang = _resolve_lang(region, source_lang)
        crop = _crop(page_image, region.box)
        if crop is None:
            region.source_text = ""
            region.conf = 0.0
            continue

        cache_key = None
        if cache is not None:
            # Include crop shape: tobytes() drops (H, W), so different-shaped crops
            # with the same flat buffer would otherwise collide to one OCR result.
            cache_key = (
                f"{lang}:{crop.shape[0]}x{crop.shape[1]}:{hashlib.sha1(crop.tobytes()).hexdigest()}"
            )
        cached = cache.get(cache_key) if cache_key is not None else None
        if cached is not None:
            text, conf, used = cached
        else:
            engine = engine_cache.get(lang)
            if engine is None:
                engine = build_engine(lang, config)
                engine_cache[lang] = engine

            result = engine.recognize(crop)
            text, conf, used = result.text, result.conf, result.engine

            if escalate and _should_escalate(region, text, conf, conf_threshold):
                escalator = vlm if vlm is not None else engine_cache.get("vlm")
                if escalator is None and vlm is None and "vlm" not in engine_cache:
                    escalator = _maybe_build_vlm(config)
                    engine_cache["vlm"] = escalator
                if escalator is not None:
                    vres = escalator.recognize(crop)
                    if vres.text.strip():
                        text, conf, used = vres.text, vres.conf, vres.engine

            if cache_key is not None:
                cache[cache_key] = (text, conf, used)

        region.source_text = text.strip()
        detected = detect_script(region.source_text)
        if not region.lang:
            region.lang = detected or (lang if lang != "auto" else "")
        region.conf = float(conf)

        if log_cb:
            shown = conf if conf != _NO_CONF else float("nan")
            log_cb(
                f"[ocr] cls={region.cls} lang={region.lang or lang} engine={used} "
                f"conf={shown:.2f} chars={len(region.source_text)}"
            )

    return region_list


def _maybe_build_vlm(config) -> Optional[OcrEngine]:
    """Construct the VLM escalator if its model id is configured; else None."""

    model_key = getattr(config, "ocr_vlm_model", None) if config else None
    device = getattr(config, "device", "auto") if config else "auto"
    if not model_key:
        return None
    return PaddleVlmEngine(model_key=model_key, device=device)
