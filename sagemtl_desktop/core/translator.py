"""
Translation engine with pluggable backends and chunked processing.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple


class MissingTranslatorError(Exception):
    """Raised when a required translation model is not installed."""

    def __init__(self, source_lang: str, target_lang: str, available_pairs: Optional[List[Tuple[str, str]]] = None):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.available_pairs = available_pairs or []

        message = (
            f"Translation model not found for {source_lang} → {target_lang}.\n\n"
            f"Please install the required language pack:\n"
            f"  python -c \"import argostranslate.package; "
            f"argostranslate.package.update_package_index(); "
            f"pkg = [p for p in argostranslate.package.get_available_packages() "
            f"if p.from_code == '{source_lang}' and p.to_code == '{target_lang}'][0]; "
            f"argostranslate.package.install_from_path(pkg.download())\"\n"
        )

        if self.available_pairs:
            pairs = ", ".join(f"{src}→{dst}" for src, dst in self.available_pairs[:5])
            message += f"\nAvailable installed models: {pairs}"

        super().__init__(message)


class Translator:
    """Translation wrapper supporting multiple backends."""

    DEFAULT_BACKEND = "argos"
    SUPPORTED_BACKENDS = ("argos", "googletrans", "echo")
    _CJK_LANGS: Set[str] = {"zh", "ja", "ko"}
    _PRIMARY_BOUNDARY_MAP = {
        "default": {".", "!", "?", ";"},
        "zh": {".", "!", "?", ";", "。", "！", "？", "；"},
        "ja": {".", "!", "?", ";", "。", "！", "？", "；"},
        "ko": {".", "!", "?", ";", "。", "！", "？", "；"},
    }
    _SECONDARY_BOUNDARY_MAP = {
        "default": {",", ":"},
        "zh": {",", ":", "，", "：", "、"},
        "ja": {",", ":", "，", "：", "、"},
        "ko": {",", ":", "，", "：", "、"},
    }
    _POST_BOUNDARY_CHARS = set("\"'”’）)]}」』")

    def __init__(self):
        self.installed_languages: Dict[str, object] = {}
        self._argos_available = False
        self._active_backend = self.DEFAULT_BACKEND
        self._translation_cache: Dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_entries = 50000
        self._load_argos()

    def _load_argos(self):
        """Load Argos Translate and installed language packs."""
        try:
            import argostranslate.package
            import argostranslate.translate  # noqa: F401

            self._argos_available = True

            try:
                argostranslate.package.update_package_index()
            except Exception as exc:
                print(f"Warning: Could not update Argos package index: {exc}")

            installed = argostranslate.package.get_installed_packages()
            self.installed_languages.clear()
            for pkg in installed:
                key = f"{pkg.from_code}→{pkg.to_code}"
                self.installed_languages[key] = pkg

            print(f"Loaded {len(self.installed_languages)} Argos translation models")
        except ImportError:
            print("ERROR: Argos Translate not installed!")
            print("Install with: pip install argostranslate")
            self._argos_available = False

    def get_active_backend(self) -> str:
        """Return current translation backend."""
        return self._active_backend

    def set_active_backend(self, backend: str):
        """Set active translation backend."""
        backend_name = self._normalize_backend_name(backend)
        self._active_backend = backend_name

    def is_available(self, backend: Optional[str] = None) -> bool:
        """Check whether a backend is available."""
        backend_name = self._normalize_backend_name(backend or self._active_backend)
        if backend_name == "argos":
            return self._argos_available
        if backend_name == "googletrans":
            try:
                import googletrans  # noqa: F401
            except Exception:
                return False
            return True
        if backend_name == "echo":
            return True
        return False

    def get_supported_backends(self) -> List[Dict[str, object]]:
        """Return backend metadata for UI and diagnostics."""
        return [
            {
                "name": "argos",
                "label": "Argos Translate (offline)",
                "available": self.is_available("argos"),
                "hint": "Install with: pip install argostranslate",
            },
            {
                "name": "googletrans",
                "label": "Google Translate (googletrans)",
                "available": self.is_available("googletrans"),
                "hint": "Install with: pip install googletrans==4.0.0rc1",
            },
            {
                "name": "echo",
                "label": "Echo (no translation)",
                "available": True,
                "hint": "Useful for pipeline testing",
            },
        ]

    def get_available_languages(self) -> List[Tuple[str, str, str]]:
        """
        Get list of available Argos language pairs.

        Returns:
            List of tuples (source_code, target_code, display_name).
        """
        if not self._argos_available:
            return []

        try:
            import argostranslate.package

            installed = argostranslate.package.get_installed_packages()
            return [
                (pkg.from_code, pkg.to_code, f"{pkg.from_name} → {pkg.to_name}")
                for pkg in installed
            ]
        except Exception as exc:
            print(f"Error getting languages: {exc}")
            return []

    def detect_language(self, text: str) -> str:
        """
        Detect language of input text using Unicode heuristics.

        Args:
            text: Text to detect language for.

        Returns:
            Language code (e.g., 'zh', 'ja', 'ko', 'en').
        """
        sample = text[:500]
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", sample))
        japanese_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", sample))
        korean_chars = len(re.findall(r"[\uac00-\ud7af]", sample))

        total_chars = len(sample.strip())
        if total_chars == 0:
            return "en"

        threshold = 0.2
        if chinese_chars / total_chars > threshold:
            return "zh"
        if japanese_chars / total_chars > threshold:
            return "ja"
        if korean_chars / total_chars > threshold:
            return "ko"
        return "en"

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        backend: Optional[str] = None,
        max_chunk_size: int = 900,
    ) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Input text.
            source_lang: Source language code or ``auto``.
            target_lang: Target language code.
            progress_callback: Function to call with progress (0-100).
            log_callback: Function to call with ``(level, message)``.
            backend: Optional backend override.
            max_chunk_size: Maximum chunk length in characters.

        Returns:
            Translated text.
        """
        backend_name = self._normalize_backend_name(backend or self._active_backend)
        if not self.is_available(backend_name):
            raise RuntimeError(self._backend_unavailable_message(backend_name))

        detected_source = source_lang
        if source_lang == "auto":
            detected_source = self.detect_language(text)
            if log_callback:
                log_callback("info", f"Auto-detected language: {detected_source}")

        if log_callback:
            log_callback("info", f"Starting translation {source_lang}→{target_lang} via {backend_name}")

        backend_source_lang = detected_source if backend_name == "argos" and source_lang == "auto" else source_lang
        chunk_translate = self._build_chunk_translator(
            backend_name=backend_name,
            source_lang=backend_source_lang,
            target_lang=target_lang,
            log_callback=log_callback,
        )

        chunk_lang = detected_source if source_lang == "auto" else source_lang
        chunks = self._split_into_chunks(
            text,
            source_lang=chunk_lang,
            max_length=max_chunk_size,
        )
        total_chunks = len(chunks)

        if log_callback:
            log_callback("info", f"Split into {total_chunks} chunks for translation")

        translated_chunks: List[str] = []
        for index, chunk in enumerate(chunks):
            if not chunk:
                translated_chunks.append(chunk)
                continue

            try:
                cache_key = self._cache_key(backend_name, source_lang, target_lang, chunk)
                cached = self._translation_cache.get(cache_key)
                if cached is not None:
                    translated = cached
                    self._cache_hits += 1
                else:
                    translated = chunk_translate(chunk)
                    self._set_cached_translation(cache_key, translated)
                    self._cache_misses += 1
                translated_chunks.append(translated)

                if log_callback and index % 10 == 0:
                    log_callback("info", f"Translated chunk {index + 1}/{total_chunks}")
            except Exception as exc:
                if log_callback:
                    log_callback("warn", f"Failed to translate chunk {index + 1}: {exc}")
                translated_chunks.append(chunk)

            if progress_callback and total_chunks > 0:
                progress_callback(((index + 1) / total_chunks) * 100)

        result = "".join(translated_chunks)
        if log_callback:
            log_callback("info", f"Translation completed ({len(result)} characters)")
        return result

    def _build_chunk_translator(
        self,
        backend_name: str,
        source_lang: str,
        target_lang: str,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Callable[[str], str]:
        if backend_name == "echo":
            return lambda value: value
        if backend_name == "googletrans":
            return self._build_googletrans_chunk_translator(source_lang, target_lang)
        if backend_name == "argos":
            return self._build_argos_chunk_translator(source_lang, target_lang, log_callback)
        raise RuntimeError(f"Unsupported translation backend: {backend_name}")

    def _build_argos_chunk_translator(
        self,
        source_lang: str,
        target_lang: str,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Callable[[str], str]:
        argos_source_lang = source_lang
        if source_lang == "auto":
            raise RuntimeError("Argos backend requires explicit source language after auto-detection")
        try:
            import argostranslate.translate

            translation = argostranslate.translate.get_translation_from_codes(
                argos_source_lang,
                target_lang,
            )
            if translation is None:
                import argostranslate.package

                available = [
                    (pkg.from_code, pkg.to_code)
                    for pkg in argostranslate.package.get_installed_packages()
                ]
                raise MissingTranslatorError(argos_source_lang, target_lang, available)
            return translation.translate
        except MissingTranslatorError:
            if log_callback:
                log_callback("error", f"Missing translation model: {argos_source_lang}→{target_lang}")
            raise
        except Exception as exc:
            if log_callback:
                log_callback("error", f"Translation model error: {exc}")
            try:
                import argostranslate.package

                available = [
                    (pkg.from_code, pkg.to_code)
                    for pkg in argostranslate.package.get_installed_packages()
                ]
            except Exception:
                available = []
            raise MissingTranslatorError(argos_source_lang, target_lang, available)

    @staticmethod
    def _build_googletrans_chunk_translator(source_lang: str, target_lang: str) -> Callable[[str], str]:
        try:
            from googletrans import Translator as GoogleTranslator
        except Exception as exc:
            raise RuntimeError(
                "googletrans backend is unavailable. Install with: pip install googletrans==4.0.0rc1"
            ) from exc

        translator = GoogleTranslator()
        src_code = source_lang if source_lang and source_lang != "auto" else "auto"

        def _translate_chunk(chunk: str) -> str:
            translated = translator.translate(chunk, src=src_code, dest=target_lang)
            return getattr(translated, "text", chunk)

        return _translate_chunk

    def _normalize_backend_name(self, backend: str) -> str:
        backend_name = (backend or "").strip().lower()
        if backend_name not in self.SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported translation backend: {backend}. "
                f"Supported: {', '.join(self.SUPPORTED_BACKENDS)}"
            )
        return backend_name

    def _backend_unavailable_message(self, backend_name: str) -> str:
        if backend_name == "argos":
            return "Argos Translate is not installed. Install with: pip install argostranslate"
        if backend_name == "googletrans":
            return "googletrans backend is not installed. Install with: pip install googletrans==4.0.0rc1"
        return f"Translation backend is unavailable: {backend_name}"

    @staticmethod
    def _cache_key(backend: str, source_lang: str, target_lang: str, chunk: str) -> str:
        """Build deterministic cache key for a translation chunk."""
        return f"{backend}|{source_lang}|{target_lang}|{chunk}"

    def _set_cached_translation(self, key: str, value: str):
        """Insert into bounded in-memory translation cache."""
        if len(self._translation_cache) >= self._max_cache_entries:
            oldest_key = next(iter(self._translation_cache))
            del self._translation_cache[oldest_key]
        self._translation_cache[key] = value

    def clear_translation_cache(self):
        """Clear in-memory translation cache."""
        self._translation_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_translation_cache_stats(self) -> Dict[str, int]:
        """Expose cache stats for diagnostics/testing."""
        return {
            "entries": len(self._translation_cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
        }

    def _split_into_sentences(
        self,
        text: str,
        max_length: int = 500,
        source_lang: str = "auto",
    ) -> List[str]:
        """
        Backward-compatible wrapper for chunking logic.

        Args:
            text: Input text.
            max_length: Maximum characters per chunk.
            source_lang: Source language hint.
        """
        return self._split_into_chunks(text, source_lang=source_lang, max_length=max_length)

    def _split_into_chunks(
        self,
        text: str,
        source_lang: str = "auto",
        max_length: int = 900,
    ) -> List[str]:
        """Split text into translation chunks while preserving source spacing."""
        if not text:
            return []

        normalized_max = self._normalize_chunk_size(max_length)
        language = source_lang if source_lang and source_lang != "auto" else self.detect_language(text)
        primary_boundaries = self._PRIMARY_BOUNDARY_MAP.get(language, self._PRIMARY_BOUNDARY_MAP["default"])
        secondary_boundaries = self._SECONDARY_BOUNDARY_MAP.get(language, self._SECONDARY_BOUNDARY_MAP["default"])

        segments = self._split_on_boundaries(text, primary_boundaries)
        expanded_segments: List[str] = []
        for segment in segments:
            if len(segment) <= normalized_max:
                expanded_segments.append(segment)
                continue
            expanded_segments.extend(
                self._split_oversized_segment(segment, normalized_max, secondary_boundaries, language)
            )

        chunks: List[str] = []
        current = ""
        for segment in expanded_segments:
            if not segment:
                continue

            if len(segment) > normalized_max:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._hard_split(segment, normalized_max))
                continue

            if not current:
                current = segment
                continue

            if len(current) + len(segment) <= normalized_max:
                current += segment
            else:
                chunks.append(current)
                current = segment

        if current:
            chunks.append(current)

        return chunks or [text]

    @staticmethod
    def _normalize_chunk_size(max_length: int) -> int:
        if max_length <= 0:
            return 900
        return max(100, int(max_length))

    def _split_oversized_segment(
        self,
        segment: str,
        max_length: int,
        secondary_boundaries: Set[str],
        language: str,
    ) -> List[str]:
        secondary_segments = self._split_on_boundaries(segment, secondary_boundaries)
        if len(secondary_segments) == 1 and secondary_segments[0] == segment:
            return self._split_by_word_or_character(segment, max_length, language)

        reduced: List[str] = []
        for piece in secondary_segments:
            if len(piece) <= max_length:
                reduced.append(piece)
            else:
                reduced.extend(self._split_by_word_or_character(piece, max_length, language))
        return reduced

    def _split_by_word_or_character(self, segment: str, max_length: int, language: str) -> List[str]:
        if language not in self._CJK_LANGS and re.search(r"\s", segment):
            tokens = re.findall(r"\S+\s*", segment)
            if tokens:
                pieces: List[str] = []
                current = ""
                for token in tokens:
                    if len(token) > max_length:
                        if current:
                            pieces.append(current)
                            current = ""
                        pieces.extend(self._hard_split(token, max_length))
                        continue
                    if not current:
                        current = token
                    elif len(current) + len(token) <= max_length:
                        current += token
                    else:
                        pieces.append(current)
                        current = token
                if current:
                    pieces.append(current)
                if pieces:
                    return pieces

        return self._hard_split(segment, max_length)

    @staticmethod
    def _hard_split(segment: str, max_length: int) -> List[str]:
        return [segment[index:index + max_length] for index in range(0, len(segment), max_length)]

    def _split_on_boundaries(self, text: str, boundaries: Sequence[str]) -> List[str]:
        boundary_set = set(boundaries)
        segments: List[str] = []
        start = 0
        index = 0
        text_length = len(text)

        while index < text_length:
            char = text[index]
            should_split = False

            if char in boundary_set:
                should_split = True
                index += 1
                while index < text_length and text[index] in self._POST_BOUNDARY_CHARS:
                    index += 1
                while index < text_length and text[index].isspace() and text[index] != "\n":
                    index += 1
            elif char == "\n":
                should_split = True
                index += 1
                while index < text_length and text[index] == "\n":
                    index += 1
            else:
                index += 1

            if should_split:
                segments.append(text[start:index])
                start = index

        if start < text_length:
            segments.append(text[start:])
        return segments

    def install_language_pack(
        self,
        from_code: str,
        to_code: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ):
        """
        Install an Argos language pack (downloads from internet).

        Args:
            from_code: Source language code.
            to_code: Target language code.
            progress_callback: Progress callback (0-100).
        """
        del progress_callback
        if not self._argos_available:
            raise RuntimeError("Argos Translate is not installed")

        try:
            import argostranslate.package

            argostranslate.package.update_package_index()

            available_packages = argostranslate.package.get_available_packages()
            package_to_install = None
            for pkg in available_packages:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    package_to_install = pkg
                    break

            if not package_to_install:
                raise ValueError(f"No package available for {from_code}→{to_code}")

            print(f"Downloading {package_to_install.from_name} → {package_to_install.to_name}...")
            download_path = package_to_install.download()

            print("Installing...")
            argostranslate.package.install_from_path(download_path)
            self._load_argos()
            print(f"Successfully installed {from_code}→{to_code}")
        except Exception as exc:
            print(f"Failed to install language pack: {exc}")
            raise
