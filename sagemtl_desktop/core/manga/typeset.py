"""Stage 5: typeset / re-letter.

Renders the translated text back into each region with Pillow: binary-search the
font size, greedily wrap to the bubble width, draw centered with a contrasting
stroke outline. Text color and outline are estimated from the cleaned bubble
background (dark text + light outline on light bubbles, and vice versa). Ships
only OFL fonts (Comic Neue default). All heavy imports are lazy.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 8.1.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

from .detect import TEXT_CLASSES
from .models import TextRegion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np
    from PIL import ImageFont

__all__ = ["render", "fit_text", "wrap_text", "resolve_font_path", "DEFAULT_FONT_PATH"]

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
DEFAULT_FONT_PATH = _FONTS_DIR / "ComicNeue-Bold.ttf"
_MIN_FONT = 8
_PADDING_FRAC = 0.08


def resolve_font_path(font_path: "str | Path | None") -> str:
    """Resolve a configured font path to an existing file, else the bundled default."""

    if font_path:
        candidate = Path(font_path)
        if candidate.is_file():
            return str(candidate)
        # config stores a repo-relative path like core/manga/fonts/X.ttf
        name = candidate.name
        bundled = _FONTS_DIR / name
        if bundled.is_file():
            return str(bundled)
    return str(DEFAULT_FONT_PATH)


def _clip_box(box, width, height):
    x1 = max(0, min(int(box[0]), width))
    y1 = max(0, min(int(box[1]), height))
    x2 = max(0, min(int(box[2]), width))
    y2 = max(0, min(int(box[3]), height))
    return x1, y1, x2, y2


def _char_break(token: str, font: "ImageFont.FreeTypeFont", max_w: float) -> list[str]:
    pieces: list[str] = []
    current = ""
    for ch in token:
        if current and font.getlength(current + ch) > max_w:
            pieces.append(current)
            current = ch
        else:
            current += ch
    if current:
        pieces.append(current)
    return pieces


def wrap_text(text: str, font: "ImageFont.FreeTypeFont", max_w: float) -> list[str]:
    """Greedy word-wrap to ``max_w``; char-break tokens wider than the line."""

    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if font.getlength(current + " " + word) <= max_w:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)

    wrapped: list[str] = []
    for line in lines:
        if font.getlength(line) <= max_w or " " not in line:
            if font.getlength(line) <= max_w:
                wrapped.append(line)
            else:
                wrapped.extend(_char_break(line, font, max_w))
        else:
            wrapped.append(line)
    return wrapped


def _line_height(font: "ImageFont.FreeTypeFont") -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def fit_text(
    text: str,
    font_path: str,
    max_w: float,
    max_h: float,
    *,
    min_font: int = _MIN_FONT,
    max_font: Optional[int] = None,
) -> "tuple[int, list[str], ImageFont.FreeTypeFont]":
    """Binary-search the largest font size whose wrapped text fits ``max_w x max_h``."""

    from PIL import ImageFont

    ceiling = int(max_font if max_font else max(min_font, max_h))
    best_size, best_lines = min_font, []
    lo, hi = min_font, max(min_font, ceiling)
    while lo <= hi:
        mid = (lo + hi) // 2
        font = ImageFont.truetype(font_path, mid)
        lines = wrap_text(text, font, max_w)
        widest = max((font.getlength(line) for line in lines), default=0.0)
        total_h = _line_height(font) * max(1, len(lines))
        if lines and widest <= max_w and total_h <= max_h:
            best_size, best_lines = mid, lines
            lo = mid + 1
        else:
            hi = mid - 1

    font = ImageFont.truetype(font_path, best_size)
    if not best_lines:
        best_lines = wrap_text(text, font, max_w) or [text]
    return best_size, best_lines, font


def _estimate_colors(clean_rgb: "np.ndarray", box) -> tuple[tuple, tuple]:
    import numpy as np

    x1, y1, x2, y2 = box
    crop = clean_rgb[y1:y2, x1:x2]
    if crop.size == 0:
        return (0, 0, 0), (255, 255, 255)
    bg = np.median(crop.reshape(-1, crop.shape[2]), axis=0)
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    if luminance >= 128:
        return (0, 0, 0), (255, 255, 255)        # dark text, light outline
    return (255, 255, 255), (0, 0, 0)            # light text, dark outline


def render(
    clean_rgb: "np.ndarray",
    regions: Sequence[TextRegion],
    *,
    font_path: "str | Path | None" = None,
    target_lang: str = "en",
    padding: float = _PADDING_FRAC,
    min_font: int = _MIN_FONT,
    classes: tuple[str, ...] = TEXT_CLASSES,
) -> "np.ndarray":
    """Draw each region's ``target_text`` into the cleaned page; return RGB array."""

    import numpy as np
    from PIL import Image, ImageDraw

    resolved_font = resolve_font_path(font_path)
    image = Image.fromarray(np.ascontiguousarray(clean_rgb.copy())).convert("RGB")
    height, width = clean_rgb.shape[:2]

    for region in regions:
        if region.cls not in classes:
            continue
        text = (region.target_text or "").strip()
        if not text:
            continue
        x1, y1, x2, y2 = _clip_box(region.box, width, height)
        box_w, box_h = x2 - x1, y2 - y1
        if box_w <= 2 or box_h <= 2:
            continue

        pad = int(min(box_w, box_h) * padding)
        avail_w = max(1, box_w - 2 * pad)
        avail_h = max(1, box_h - 2 * pad)
        text_color, stroke_color = _estimate_colors(clean_rgb, (x1, y1, x2, y2))
        size, lines, font = fit_text(text, resolved_font, avail_w, avail_h, min_font=min_font)
        stroke_width = max(1, round(size / 14))

        # Draw onto a box-sized RGBA layer and paste it clipped, so text can never
        # spill outside the bubble even when it does not fit at min_font.
        layer = Image.new("RGBA", (avail_w, avail_h), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(layer)
        line_h = _line_height(font)
        block_h = line_h * len(lines)
        cursor_y = max(0, (avail_h - block_h) // 2)
        for line in lines:
            line_w = font.getlength(line)
            cursor_x = max(0.0, (avail_w - line_w) / 2)
            ldraw.text(
                (cursor_x, cursor_y), line, font=font, fill=text_color + (255,),
                stroke_width=stroke_width, stroke_fill=stroke_color + (255,),
            )
            cursor_y += line_h
        image.paste(layer, (x1 + pad, y1 + pad), layer)

    return np.asarray(image.convert("RGB"))
