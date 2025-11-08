"""
Translation engine using Argos Translate for offline translation.
"""

import re
from typing import Callable, List, Tuple, Optional


class Translator:
    """Argos Translate wrapper for offline translation"""

    def __init__(self):
        self.installed_languages = {}
        self._argos_available = False
        self._load_argos()

    def _load_argos(self):
        """Load Argos Translate and installed language packs"""
        try:
            import argostranslate.package
            import argostranslate.translate

            self._argos_available = True

            # Update package index
            try:
                argostranslate.package.update_package_index()
            except Exception as e:
                print(f"Warning: Could not update Argos package index: {e}")

            # Load installed packages
            installed = argostranslate.package.get_installed_packages()

            for pkg in installed:
                key = f"{pkg.from_code}→{pkg.to_code}"
                self.installed_languages[key] = pkg

            print(f"Loaded {len(self.installed_languages)} Argos translation models")

        except ImportError:
            print("ERROR: Argos Translate not installed!")
            print("Install with: pip install argostranslate")
            self._argos_available = False

    def is_available(self) -> bool:
        """Check if Argos Translate is available"""
        return self._argos_available

    def get_available_languages(self) -> List[Tuple[str, str, str]]:
        """
        Get list of available (source, target, name) language pairs.

        Returns:
            List of tuples (source_code, target_code, display_name)
            e.g., [('zh', 'en', 'Chinese → English'), ...]
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
        except Exception as e:
            print(f"Error getting languages: {e}")
            return []

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Input text
            source_lang: Source language code (e.g., 'zh', 'ja', 'ko')
            target_lang: Target language code (e.g., 'en')
            progress_callback: Function to call with progress (0-100)
            log_callback: Function to call with (level, message)

        Returns:
            Translated text

        Raises:
            RuntimeError: If Argos Translate is not available
            ValueError: If language pair is not installed
        """
        if not self._argos_available:
            raise RuntimeError("Argos Translate is not installed")

        if log_callback:
            log_callback("info", f"Starting translation {source_lang}→{target_lang}")

        # Get translation model
        try:
            import argostranslate.translate

            translation = argostranslate.translate.get_translation_from_codes(
                source_lang, target_lang
            )

            if translation is None:
                raise ValueError(f"No translation model for {source_lang}→{target_lang}")

        except Exception as e:
            if log_callback:
                log_callback("error", f"Translation model not found: {e}")
            raise ValueError(f"No translation model for {source_lang}→{target_lang}: {e}")

        # Split text into chunks (by sentences)
        chunks = self._split_into_sentences(text)
        total_chunks = len(chunks)

        if log_callback:
            log_callback("info", f"Split into {total_chunks} chunks for translation")

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                translated_chunks.append(chunk)
                continue

            # Translate chunk
            try:
                translated = translation.translate(chunk)
                translated_chunks.append(translated)

                if log_callback and i % 10 == 0:  # Log every 10 chunks
                    log_callback("info", f"Translated chunk {i+1}/{total_chunks}")

            except Exception as e:
                if log_callback:
                    log_callback("warn", f"Failed to translate chunk {i+1}: {e}")
                # Keep original on error
                translated_chunks.append(chunk)

            # Update progress
            if progress_callback:
                progress = ((i + 1) / total_chunks) * 100
                progress_callback(progress)

        # Join chunks back together
        result = " ".join(translated_chunks)

        if log_callback:
            log_callback("info", f"Translation completed ({len(result)} characters)")

        return result

    def _split_into_sentences(self, text: str, max_length: int = 500) -> List[str]:
        """
        Split text into sentences for chunked processing.

        Args:
            text: Input text
            max_length: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        # Split on sentence boundaries
        # Handles English (. ! ?), Chinese (。！？), Japanese (。！？)
        sentence_pattern = r'([.!?。！？]\s*)'
        parts = re.split(sentence_pattern, text)

        # Recombine sentence and punctuation
        chunks = []
        current_chunk = ""

        i = 0
        while i < len(parts):
            sentence = parts[i]

            # Add punctuation if it exists
            if i + 1 < len(parts) and re.match(sentence_pattern, parts[i + 1]):
                sentence += parts[i + 1]
                i += 2
            else:
                i += 1

            # Add to current chunk or start new chunk
            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If no sentences were found, split by length
        if not chunks:
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]

        return chunks

    def install_language_pack(
        self,
        from_code: str,
        to_code: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        Install a language pack (downloads from internet).

        Args:
            from_code: Source language code
            to_code: Target language code
            progress_callback: Progress callback (0-100)

        Note: This requires internet access and is used for initial setup.
        For offline operation, language packs should be pre-bundled.
        """
        if not self._argos_available:
            raise RuntimeError("Argos Translate is not installed")

        try:
            import argostranslate.package

            # Update package index
            argostranslate.package.update_package_index()

            # Find available package
            available_packages = argostranslate.package.get_available_packages()
            package_to_install = None

            for pkg in available_packages:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    package_to_install = pkg
                    break

            if not package_to_install:
                raise ValueError(f"No package available for {from_code}→{to_code}")

            # Download and install
            print(f"Downloading {package_to_install.from_name} → {package_to_install.to_name}...")
            download_path = package_to_install.download()

            print(f"Installing...")
            argostranslate.package.install_from_path(download_path)

            # Reload installed languages
            self._load_argos()

            print(f"Successfully installed {from_code}→{to_code}")

        except Exception as e:
            print(f"Failed to install language pack: {e}")
            raise
