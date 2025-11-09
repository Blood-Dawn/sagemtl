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

        Returns:
            dict: Validation results with warnings if any
        """
        self.glossary_path = Path(path)

        if not self.glossary_path.exists():
            raise FileNotFoundError(f"Glossary file not found: {path}")

        self.entries = []
        warnings = []

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Support multiple CSV formats:
            # 1. Standard format: 'source' and 'target' columns
            # 2. Alternative format: 'English' and 'Chinese' columns
            # 3. Category-based format: 'Category', 'English', 'Chinese' columns
            
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")
            
            # Determine which columns to use
            source_col = None
            target_col = None
            
            # Check for standard format
            if 'source' in reader.fieldnames and 'target' in reader.fieldnames:
                source_col = 'source'
                target_col = 'target'
            # Check for English/Chinese format
            elif 'English' in reader.fieldnames and 'Chinese' in reader.fieldnames:
                source_col = 'Chinese'  # For translation, Chinese is source
                target_col = 'English'   # English is target
            else:
                # Show available columns to help user
                available = ', '.join(reader.fieldnames)
                raise ValueError(
                    f"CSV must have either 'source'/'target' or 'English'/'Chinese' columns. "
                    f"Available columns: {available}"
                )

            # Check for recommended columns (only check if using standard format)
            if source_col == 'source':
                recommended_columns = ['source', 'target', 'case_sensitive', 'word_boundary', 'notes']
                missing_columns = [col for col in recommended_columns if col not in reader.fieldnames]

                if missing_columns:
                    warnings.append(
                        f"Optional column(s) missing: {', '.join(missing_columns)}. "
                        f"Defaults will be used."
                    )

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    entry = GlossaryEntry(
                        source=row[source_col].strip(),
                        target=row[target_col].strip(),
                        case_sensitive=row.get('case_sensitive', 'true').lower() == 'true',
                        word_boundary=row.get('word_boundary', 'false').lower() == 'true',
                        notes=row.get('notes', '').strip()
                    )

                    if not entry.source or not entry.target:
                        warnings.append(f"Row {row_num}: Empty source or target, skipping")
                        continue

                    self.entries.append(entry)

                except KeyError as e:
                    raise ValueError(f"Missing required column in CSV: {e}")

        # Sort by length (longest first) to avoid partial replacements
        # E.g., "Sect Master" should be replaced before "Sect"
        self.entries.sort(key=lambda e: len(e.source), reverse=True)

        print(f"Loaded {len(self.entries)} glossary entries from {path}")

        return {
            'entries_loaded': len(self.entries),
            'warnings': warnings
        }

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

    @property
    def before_entries(self) -> List[GlossaryEntry]:
        """Get entries applied before translation (all entries for now)"""
        return self.entries

    @property
    def after_entries(self) -> List[GlossaryEntry]:
        """Get entries applied after translation (all entries for now)"""
        return self.entries

    def clear(self):
        """Clear loaded glossary"""
        self.entries = []
        self.glossary_path = None
