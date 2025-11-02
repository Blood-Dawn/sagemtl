"""Text normalisation helpers with configurable toggles."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping

__all__ = ["NormalizeOptions", "normalize_text", "basic_clean"]


@dataclass(slots=True)
class NormalizeOptions:
    """Control switches for :func:`normalize_text`.

    Each field maps directly to a transformation that can be toggled on or
    off.  Options default to ``True`` so the historical behaviour (all
    clean-ups enabled) remains unchanged for existing callers.
    """

    smart_quotes: bool = True
    em_dash: bool = True
    minus_sign: bool = True
    nbsp_to_space: bool = True
    zero_width: bool = True
    collapse_blank_lines: bool = True
    ensure_trailing_lf: bool = True

    def build_translation_table(self) -> Mapping[int, str]:
        table: dict[int, str] = {}
        if self.smart_quotes:
            table.update(
                {
                    ord("\u2018"): "'",
                    ord("\u2019"): "'",
                    ord("\u201b"): "'",
                    ord("\u201c"): '"',
                    ord("\u201d"): '"',
                    ord("\u2026"): "...",
                }
            )
        if self.em_dash:
            table.update({ord("\u2013"): "-", ord("\u2014"): "-"})
        if self.minus_sign:
            table[ord("\u2212")] = "-"
        if self.nbsp_to_space:
            table[ord("\u00a0")] = " "
        return table


_ZERO_WIDTH = ("\u200b", "\u200c", "\u200d", "\ufeff", "\u2060")


def _strip_trailing_ws(text: str) -> str:
    return "\n".join(re.sub(r"[ \t]+$", "", line) for line in text.splitlines())


def normalize_text(text: str, options: NormalizeOptions | None = None) -> str:
    """Normalise typography, whitespace and newline usage.

    Parameters
    ----------
    text:
        Text to normalise. Non-string inputs are coerced using ``str``.
    options:
        :class:`NormalizeOptions` controlling which clean-up passes are applied.
    """

    if not isinstance(text, str):
        text = str(text)

    opts = options or NormalizeOptions()

    if opts.zero_width:
        for marker in _ZERO_WIDTH:
            text = text.replace(marker, "")
    else:
        text = text.replace("\ufeff", "")  # Always drop BOM

    text = text.translate(opts.build_translation_table())

    text = unicodedata.normalize("NFKC", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = _strip_trailing_ws(text)

    if opts.collapse_blank_lines:
        text = re.sub(r"\n{3,}", "\n\n", text)

    if opts.ensure_trailing_lf and not text.endswith("\n"):
        text += "\n"

    return text


def basic_clean(text: str) -> str:
    """Backwards compatible helper used by older tests."""

    opts = NormalizeOptions(ensure_trailing_lf=False)
    out = normalize_text(text, options=opts)
    return out[:-1] if out.endswith("\n") else out
