"""
Advanced Glossary Manager with novel-specific and global glossaries.

Inspired by WTR Labs approach:
- Global glossary: Terms that apply to ALL novels (common MTL fixes, etc.)
- Novel glossary: Terms specific to one novel (character names, locations, etc.)
- Persistent storage: Glossaries are saved and loaded automatically
- Inline editing: Users can select text and create entries directly
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

_CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")


@dataclass
class GlossaryTerm:
    """A single glossary term mapping"""
    source: str  # Original text to match
    target: str  # Replacement text
    case_sensitive: bool = False
    word_boundary: bool = True  # Only match whole words
    category: str = ""  # e.g., "Character", "Location", "Skill", "Item"
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlossaryTerm':
        return cls(**data)


@dataclass 
class NovelGlossary:
    """Glossary specific to a single novel"""
    novel_id: str
    novel_title: str
    terms: List[GlossaryTerm] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'novel_id': self.novel_id,
            'novel_title': self.novel_title,
            'terms': [t.to_dict() for t in self.terms],
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NovelGlossary':
        terms = [GlossaryTerm.from_dict(t) for t in data.get('terms', [])]
        return cls(
            novel_id=data['novel_id'],
            novel_title=data['novel_title'],
            terms=terms,
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat())
        )


class GlossaryManager:
    """
    Manages global and novel-specific glossaries with persistence.
    
    Storage structure:
    - ~/.sagemtl/glossaries/global.json - Global glossary
    - ~/.sagemtl/glossaries/novels/<novel_id>.json - Per-novel glossaries
    """
    
    # Common categories for organization
    CATEGORIES = [
        "Character",
        "Location", 
        "Skill/Ability",
        "Item/Artifact",
        "Organization",
        "Title/Rank",
        "Cultivation",
        "Other"
    ]
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the glossary manager.
        
        Args:
            storage_dir: Directory for storing glossaries. Defaults to ~/.sagemtl/glossaries
        """
        if storage_dir is None:
            storage_dir = Path.home() / '.sagemtl' / 'glossaries'
        
        self.storage_dir = Path(storage_dir)
        self.novels_dir = self.storage_dir / 'novels'
        
        # Create directories
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.novels_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self._global_terms: List[GlossaryTerm] = []
        self._novel_glossaries: Dict[str, NovelGlossary] = {}
        self._active_novel_id: Optional[str] = None
        self._pattern_cache: Dict[Tuple[str, bool, bool], Pattern[str]] = {}
        
        # Load global glossary
        self._load_global()
    
    # ==================== Global Glossary ====================
    
    def _global_path(self) -> Path:
        return self.storage_dir / 'global.json'
    
    def _load_global(self):
        """Load global glossary from disk"""
        path = self._global_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._global_terms = [GlossaryTerm.from_dict(t) for t in data.get('terms', [])]
                    print(f"Loaded {len(self._global_terms)} global glossary terms")
            except Exception as e:
                print(f"Error loading global glossary: {e}")
                self._global_terms = []
        else:
            self._global_terms = []
    
    def _save_global(self):
        """Save global glossary to disk"""
        path = self._global_path()
        try:
            data = {
                'terms': [t.to_dict() for t in self._global_terms],
                'updated_at': datetime.now().isoformat()
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving global glossary: {e}")

    def _invalidate_pattern_cache(self):
        """Clear cached regex patterns after glossary mutations."""
        self._pattern_cache.clear()
    
    def get_global_terms(self) -> List[GlossaryTerm]:
        """Get all global glossary terms"""
        return self._global_terms.copy()
    
    def add_global_term(self, term: GlossaryTerm) -> bool:
        """
        Add a term to the global glossary.
        
        Returns:
            True if added, False if duplicate source exists
        """
        # Check for duplicates
        for existing in self._global_terms:
            if existing.source.lower() == term.source.lower():
                return False
        
        self._global_terms.append(term)
        self._sort_terms(self._global_terms)
        self._invalidate_pattern_cache()
        self._save_global()
        return True
    
    def update_global_term(self, source: str, updated_term: GlossaryTerm) -> bool:
        """Update an existing global term"""
        for i, term in enumerate(self._global_terms):
            if term.source == source:
                self._global_terms[i] = updated_term
                self._sort_terms(self._global_terms)
                self._invalidate_pattern_cache()
                self._save_global()
                return True
        return False
    
    def remove_global_term(self, source: str) -> bool:
        """Remove a term from global glossary"""
        for i, term in enumerate(self._global_terms):
            if term.source == source:
                del self._global_terms[i]
                self._invalidate_pattern_cache()
                self._save_global()
                return True
        return False
    
    # ==================== Novel Glossary ====================
    
    def _novel_path(self, novel_id: str) -> Path:
        return self.novels_dir / f'{novel_id}.json'
    
    def load_novel_glossary(self, novel_id: str, novel_title: str = "") -> NovelGlossary:
        """
        Load or create a novel-specific glossary.
        
        Args:
            novel_id: Unique identifier for the novel
            novel_title: Title of the novel (for display)
            
        Returns:
            NovelGlossary instance
        """
        if novel_id in self._novel_glossaries:
            return self._novel_glossaries[novel_id]
        
        path = self._novel_path(novel_id)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    glossary = NovelGlossary.from_dict(data)
                    self._novel_glossaries[novel_id] = glossary
                    print(f"Loaded {len(glossary.terms)} terms for novel: {glossary.novel_title}")
                    return glossary
            except Exception as e:
                print(f"Error loading novel glossary: {e}")
        
        # Create new glossary
        glossary = NovelGlossary(novel_id=novel_id, novel_title=novel_title)
        self._novel_glossaries[novel_id] = glossary
        return glossary
    
    def _save_novel_glossary(self, novel_id: str):
        """Save a novel glossary to disk"""
        if novel_id not in self._novel_glossaries:
            return
        
        glossary = self._novel_glossaries[novel_id]
        glossary.updated_at = datetime.now().isoformat()
        
        path = self._novel_path(novel_id)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(glossary.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving novel glossary: {e}")
    
    def get_novel_terms(self, novel_id: str) -> List[GlossaryTerm]:
        """Get terms for a specific novel"""
        if not novel_id:
            return []
        
        # Load glossary if not already loaded
        if novel_id not in self._novel_glossaries:
            self.load_novel_glossary(novel_id)
        
        if novel_id in self._novel_glossaries:
            return self._novel_glossaries[novel_id].terms.copy()
        return []
    
    def add_novel_term(self, novel_id: str, term: GlossaryTerm) -> bool:
        """Add a term to a novel's glossary"""
        if not novel_id:
            return False
        
        # Load glossary if not already loaded
        if novel_id not in self._novel_glossaries:
            self.load_novel_glossary(novel_id)
        
        if novel_id not in self._novel_glossaries:
            return False
        
        glossary = self._novel_glossaries[novel_id]
        
        # Check for duplicates
        for existing in glossary.terms:
            if existing.source.lower() == term.source.lower():
                return False
        
        glossary.terms.append(term)
        self._sort_terms(glossary.terms)
        self._invalidate_pattern_cache()
        self._save_novel_glossary(novel_id)
        return True
    
    def update_novel_term(self, novel_id: str, source: str, updated_term: GlossaryTerm) -> bool:
        """Update an existing novel term"""
        if novel_id not in self._novel_glossaries:
            return False
        
        glossary = self._novel_glossaries[novel_id]
        for i, term in enumerate(glossary.terms):
            if term.source == source:
                glossary.terms[i] = updated_term
                self._sort_terms(glossary.terms)
                self._invalidate_pattern_cache()
                self._save_novel_glossary(novel_id)
                return True
        return False
    
    def remove_novel_term(self, novel_id: str, source: str) -> bool:
        """Remove a term from a novel's glossary"""
        if novel_id not in self._novel_glossaries:
            return False
        
        glossary = self._novel_glossaries[novel_id]
        for i, term in enumerate(glossary.terms):
            if term.source == source:
                del glossary.terms[i]
                self._invalidate_pattern_cache()
                self._save_novel_glossary(novel_id)
                return True
        return False

    def set_novel_title(self, novel_id: str, novel_title: str):
        """Persist a novel glossary display title after library renames."""
        if not novel_id:
            return
        glossary = self.load_novel_glossary(novel_id, novel_title)
        if glossary.novel_title == novel_title:
            return
        glossary.novel_title = novel_title
        self._save_novel_glossary(novel_id)
    
    def set_active_novel(self, novel_id: str, novel_title: str = ""):
        """Set the currently active novel for glossary operations"""
        self._active_novel_id = novel_id
        self.load_novel_glossary(novel_id, novel_title)
    
    def get_active_novel_id(self) -> Optional[str]:
        """Get the currently active novel ID"""
        return self._active_novel_id
    
    # ==================== Text Processing ====================
    
    def _sort_terms(self, terms: List[GlossaryTerm]):
        """Sort terms by length (longest first) to prevent partial replacements"""
        terms.sort(key=lambda t: len(t.source), reverse=True)
    
    def apply_glossary(self, text: str, novel_id: Optional[str] = None) -> str:
        """
        Apply glossary replacements to text.
        
        Applies both global terms and novel-specific terms.
        Novel terms take precedence over global terms.
        
        Args:
            text: Text to process
            novel_id: Optional novel ID for novel-specific terms
            
        Returns:
            Text with glossary replacements applied
        """
        if not text:
            return text
        
        result = text
        
        # Get all applicable terms (novel terms first, then global)
        all_terms: List[GlossaryTerm] = []
        
        # Load novel glossary if needed
        if novel_id:
            if novel_id not in self._novel_glossaries:
                self.load_novel_glossary(novel_id)
            if novel_id in self._novel_glossaries:
                all_terms.extend(self._novel_glossaries[novel_id].terms)
        elif self._active_novel_id:
            if self._active_novel_id not in self._novel_glossaries:
                self.load_novel_glossary(self._active_novel_id)
            if self._active_novel_id in self._novel_glossaries:
                all_terms.extend(self._novel_glossaries[self._active_novel_id].terms)
        
        all_terms.extend(self._global_terms)
        
        if not all_terms:
            return text  # No terms to apply
        
        # Sort by length to prevent partial replacements
        self._sort_terms(all_terms)
        
        # Apply replacements
        for term in all_terms:
            result = self._replace_term(result, term)
        
        return result
    
    def _replace_term(self, text: str, term: GlossaryTerm) -> str:
        """Apply a single term replacement"""
        pattern = self._get_compiled_pattern(term)
        try:
            return pattern.sub(term.target, text)
        except re.error as e:
            print(f"Regex error for term '{term.source}': {e}")
            return text

    def _get_compiled_pattern(self, term: GlossaryTerm) -> Pattern[str]:
        """Get cached compiled regex pattern for a glossary term."""
        cache_key = (term.source, term.case_sensitive, term.word_boundary)
        cached = self._pattern_cache.get(cache_key)
        if cached is not None:
            return cached

        flags = 0 if term.case_sensitive else re.IGNORECASE
        if self._use_word_boundaries(term):
            pattern = r'\b' + re.escape(term.source) + r'\b'
        else:
            pattern = re.escape(term.source)

        compiled = re.compile(pattern, flags=flags)
        self._pattern_cache[cache_key] = compiled
        return compiled

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        """Detect CJK scripts where regex word boundaries do not behave well."""
        return bool(_CJK_CHAR_RE.search(text or ""))

    @classmethod
    def _use_word_boundaries(cls, term: GlossaryTerm) -> bool:
        """
        Decide whether `\\b` boundaries should be applied.

        For CJK sources, boundaries are disabled even when requested, because
        continuous CJK text has no whitespace separators and `\\b...\\b` misses
        valid in-sentence terms.
        """
        if not term.word_boundary:
            return False
        return not cls._contains_cjk(term.source)
    
    # ==================== Import/Export ====================
    
    def import_from_csv(self, csv_path: str, target: str = 'global', novel_id: Optional[str] = None) -> dict:
        """
        Import terms from a CSV file.
        
        Args:
            csv_path: Path to CSV file
            target: 'global' or 'novel'
            novel_id: Required if target is 'novel'
            
        Returns:
            Dict with import results
        """
        import csv
        
        path = Path(csv_path)
        if not path.exists():
            return {'success': False, 'error': f"File not found: {csv_path}"}
        
        terms_added = 0
        terms_skipped = 0
        errors = []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    return {'success': False, 'error': "Empty CSV file"}
                
                # Detect column format
                source_col = None
                target_col = None
                
                if 'source' in reader.fieldnames:
                    source_col = 'source'
                    target_col = 'target'
                elif 'Source' in reader.fieldnames:
                    source_col = 'Source'
                    target_col = 'Target'
                elif 'Chinese' in reader.fieldnames:
                    source_col = 'Chinese'
                    target_col = 'English'
                elif 'original' in reader.fieldnames:
                    source_col = 'original'
                    target_col = 'replacement'
                else:
                    # Use first two columns
                    cols = list(reader.fieldnames)
                    if len(cols) >= 2:
                        source_col = cols[0]
                        target_col = cols[1]
                    else:
                        return {'success': False, 'error': "CSV must have at least 2 columns"}
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        source = row.get(source_col, '').strip()
                        target_text = row.get(target_col, '').strip()
                        
                        if not source or not target_text:
                            continue
                        
                        term = GlossaryTerm(
                            source=source,
                            target=target_text,
                            case_sensitive=row.get('case_sensitive', 'false').lower() == 'true',
                            word_boundary=row.get('word_boundary', 'true').lower() == 'true',
                            category=row.get('category', row.get('Category', '')),
                            notes=row.get('notes', row.get('Notes', ''))
                        )
                        
                        if target == 'global':
                            if self.add_global_term(term):
                                terms_added += 1
                            else:
                                terms_skipped += 1
                        elif target == 'novel' and novel_id:
                            if self.add_novel_term(novel_id, term):
                                terms_added += 1
                            else:
                                terms_skipped += 1
                    
                    except Exception as e:
                        errors.append(f"Row {row_num}: {e}")
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {
            'success': True,
            'terms_added': terms_added,
            'terms_skipped': terms_skipped,
            'errors': errors
        }
    
    def export_to_csv(self, csv_path: str, source: str = 'global', novel_id: Optional[str] = None) -> dict:
        """
        Export terms to a CSV file.
        
        Args:
            csv_path: Path for CSV file
            source: 'global', 'novel', or 'all'
            novel_id: Required if source is 'novel'
            
        Returns:
            Dict with export results
        """
        import csv
        
        terms: List[GlossaryTerm] = []
        
        if source == 'global':
            terms = self._global_terms
        elif source == 'novel' and novel_id:
            terms = self.get_novel_terms(novel_id)
        elif source == 'all':
            terms = self._global_terms.copy()
            if novel_id:
                terms.extend(self.get_novel_terms(novel_id))
        
        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['source', 'target', 'category', 'case_sensitive', 'word_boundary', 'notes'])
                
                for term in terms:
                    writer.writerow([
                        term.source,
                        term.target,
                        term.category,
                        str(term.case_sensitive).lower(),
                        str(term.word_boundary).lower(),
                        term.notes
                    ])
            
            return {'success': True, 'terms_exported': len(terms)}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> dict:
        """Get statistics about loaded glossaries"""
        novel_stats = {}
        for novel_id, glossary in self._novel_glossaries.items():
            novel_stats[novel_id] = {
                'title': glossary.novel_title,
                'term_count': len(glossary.terms)
            }
        
        return {
            'global_terms': len(self._global_terms),
            'novels_loaded': len(self._novel_glossaries),
            'active_novel': self._active_novel_id,
            'novels': novel_stats
        }
    
    def list_novel_glossaries(self) -> List[dict]:
        """List all saved novel glossaries"""
        glossaries = []
        for path in self.novels_dir.glob('*.json'):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    glossaries.append({
                        'novel_id': data.get('novel_id', path.stem),
                        'novel_title': data.get('novel_title', 'Unknown'),
                        'term_count': len(data.get('terms', [])),
                        'updated_at': data.get('updated_at', '')
                    })
            except Exception:
                pass
        return glossaries
