"""
Glossary processor for term replacement before/after translation.
"""

import csv
import re
from typing import List, Optional
from pathlib import Path
from .models import GlossaryEntry


class GlossaryProcessor:
    """Processes text using user-provided glossary"""

    def __init__(self):
        self.entries: List[GlossaryEntry] = []
        self.glossary_path: Optional[Path] = None

    def load_glossary(self, path: str):
        """
        Load glossary from CSV file.

        CSV format:
            source,target,case_sensitive,word_boundary,notes
            "Sect Master","Patriarch",true,false,"Title"
            "dao heart","resolve",true,false,"Cultivation term"

        Args:
            path: Path to CSV glossary file

        Raises:
            FileNotFoundError: If glossary file doesn't exist
            ValueError: If CSV is malformed
        """
        self.glossary_path = Path(path)

        if not self.glossary_path.exists():
            raise FileNotFoundError(f"Glossary file not found: {path}")

        self.entries = []

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames or 'source' not in reader.fieldnames or 'target' not in reader.fieldnames:
                raise ValueError("CSV must have 'source' and 'target' columns")

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    entry = GlossaryEntry(
                        source=row['source'].strip(),
                        target=row['target'].strip(),
                        case_sensitive=row.get('case_sensitive', 'true').lower() == 'true',
                        word_boundary=row.get('word_boundary', 'false').lower() == 'true',
                        notes=row.get('notes', '').strip()
                    )

                    if not entry.source or not entry.target:
                        print(f"Warning: Empty source or target at row {row_num}, skipping")
                        continue

                    self.entries.append(entry)

                except KeyError as e:
                    raise ValueError(f"Missing required column in CSV: {e}")

        # Sort by length (longest first) to avoid partial replacements
        # E.g., "Sect Master" should be replaced before "Sect"
        self.entries.sort(key=lambda e: len(e.source), reverse=True)

        print(f"Loaded {len(self.entries)} glossary entries from {path}")

    def apply_before(self, text: str) -> str:
        """
        Apply glossary before translation.

        This is used to fix known MTL fragments or preserve special terms
        before they go through the translation model.

        Args:
            text: Original source text

        Returns:
            Text with glossary replacements applied
        """
        if not self.entries:
            return text

        result = text
        for entry in self.entries:
            result = self._replace_term(result, entry)

        return result

    def apply_after(self, text: str) -> str:
        """
        Apply glossary after translation.

        This is used to enforce consistent terminology and fix awkward
        phrases that the translation model still outputs.

        Args:
            text: Translated text

        Returns:
            Text with glossary replacements applied
        """
        # Same logic for now, but could be different in future
        # (e.g., different glossary entries for before/after)
        return self.apply_before(text)

    def _replace_term(self, text: str, entry: GlossaryEntry) -> str:
        """
        Replace a single glossary term.

        Args:
            text: Input text
            entry: Glossary entry to apply

        Returns:
            Text with replacements
        """
        flags = 0 if entry.case_sensitive else re.IGNORECASE

        if entry.word_boundary:
            # Use word boundaries to avoid replacing substrings
            # E.g., "Sect" won't match inside "Section"
            pattern = r'\b' + re.escape(entry.source) + r'\b'
        else:
            # Simple string replacement
            pattern = re.escape(entry.source)

        try:
            return re.sub(pattern, entry.target, text, flags=flags)
        except re.error as e:
            print(f"Warning: Regex error for entry '{entry.source}': {e}")
            return text

    def is_loaded(self) -> bool:
        """Check if a glossary is loaded"""
        return len(self.entries) > 0

    def clear(self):
        """Clear loaded glossary"""
        self.entries = []
        self.glossary_path = None
