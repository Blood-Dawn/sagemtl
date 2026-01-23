"""
SQLite-based glossary database for consistent terminology management.

Provides persistent storage for glossary entries with features like:
- Category/tag organization
- Search and filtering
- Import/export (CSV, JSON)
- Usage statistics
- Novel-specific glossaries
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
import csv
import re
import logging

from .glossary import GlossaryEntry, apply_glossary

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntryDB(GlossaryEntry):
    """Extended glossary entry with database fields."""
    id: Optional[int] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    novel_id: Optional[str] = None  # For novel-specific entries
    priority: int = 0  # Higher priority = applied first


class GlossaryDB:
    """SQLite-based glossary database."""

    def __init__(self, db_path: Union[str, Path] = "~/.sagemtl/glossary.db"):
        """
        Initialize glossary database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Main glossary table
                CREATE TABLE IF NOT EXISTS glossary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    case_sensitive BOOLEAN DEFAULT 1,
                    word_boundary BOOLEAN DEFAULT 0,
                    notes TEXT DEFAULT '',
                    category TEXT DEFAULT 'general',
                    tags TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    novel_id TEXT,
                    priority INTEGER DEFAULT 0,
                    UNIQUE(source, novel_id)
                );

                -- Indexes for fast lookup
                CREATE INDEX IF NOT EXISTS idx_glossary_source ON glossary_entries(source);
                CREATE INDEX IF NOT EXISTS idx_glossary_category ON glossary_entries(category);
                CREATE INDEX IF NOT EXISTS idx_glossary_novel_id ON glossary_entries(novel_id);
                CREATE INDEX IF NOT EXISTS idx_glossary_priority ON glossary_entries(priority DESC);

                -- Categories table
                CREATE TABLE IF NOT EXISTS glossary_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    color TEXT DEFAULT '#808080',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Insert default categories
                INSERT OR IGNORE INTO glossary_categories (name, description, color) VALUES
                    ('general', 'General terms', '#808080'),
                    ('name', 'Character names', '#3498db'),
                    ('place', 'Location names', '#2ecc71'),
                    ('skill', 'Skills and abilities', '#e74c3c'),
                    ('item', 'Items and equipment', '#f39c12'),
                    ('title', 'Titles and ranks', '#9b59b6'),
                    ('organization', 'Organizations and factions', '#1abc9c'),
                    ('cultivation', 'Cultivation realms/terms', '#e91e63');

                -- Novels table for tracking novel-specific glossaries
                CREATE TABLE IF NOT EXISTS novels (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Usage statistics
                CREATE TABLE IF NOT EXISTS glossary_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER REFERENCES glossary_entries(id) ON DELETE CASCADE,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    novel_id TEXT
                );
            """)

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def add_entry(self, entry: GlossaryEntryDB) -> int:
        """
        Add a glossary entry to the database.

        Args:
            entry: Glossary entry to add

        Returns:
            ID of the inserted entry
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO glossary_entries
                    (source, target, case_sensitive, word_boundary, notes,
                     category, tags, novel_id, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.source,
                    entry.target,
                    entry.case_sensitive,
                    entry.word_boundary,
                    entry.notes,
                    entry.category,
                    json.dumps(entry.tags),
                    entry.novel_id,
                    entry.priority,
                )
            )
            return cursor.lastrowid

    def add_entries(self, entries: List[GlossaryEntryDB]) -> int:
        """
        Add multiple glossary entries in batch.

        Args:
            entries: List of entries to add

        Returns:
            Number of entries added
        """
        with self._get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO glossary_entries
                    (source, target, case_sensitive, word_boundary, notes,
                     category, tags, novel_id, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.source,
                        e.target,
                        e.case_sensitive,
                        e.word_boundary,
                        e.notes,
                        e.category,
                        json.dumps(e.tags),
                        e.novel_id,
                        e.priority,
                    )
                    for e in entries
                ]
            )
            return cursor.rowcount

    def get_entry(self, entry_id: int) -> Optional[GlossaryEntryDB]:
        """Get entry by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM glossary_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()

            if row:
                return self._row_to_entry(row)
            return None

    def get_entry_by_source(self, source: str, novel_id: Optional[str] = None) -> Optional[GlossaryEntryDB]:
        """Get entry by source text."""
        with self._get_connection() as conn:
            if novel_id:
                row = conn.execute(
                    "SELECT * FROM glossary_entries WHERE source = ? AND (novel_id = ? OR novel_id IS NULL)",
                    (source, novel_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM glossary_entries WHERE source = ? AND novel_id IS NULL",
                    (source,)
                ).fetchone()

            if row:
                return self._row_to_entry(row)
            return None

    def update_entry(self, entry: GlossaryEntryDB) -> bool:
        """
        Update an existing entry.

        Args:
            entry: Entry with updated values (must have id set)

        Returns:
            True if entry was updated
        """
        if entry.id is None:
            raise ValueError("Entry must have an ID to update")

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE glossary_entries SET
                    source = ?, target = ?, case_sensitive = ?, word_boundary = ?,
                    notes = ?, category = ?, tags = ?, novel_id = ?, priority = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    entry.source,
                    entry.target,
                    entry.case_sensitive,
                    entry.word_boundary,
                    entry.notes,
                    entry.category,
                    json.dumps(entry.tags),
                    entry.novel_id,
                    entry.priority,
                    entry.id,
                )
            )
            return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM glossary_entries WHERE id = ?",
                (entry_id,)
            )
            return cursor.rowcount > 0

    def delete_entries_by_novel(self, novel_id: str) -> int:
        """Delete all entries for a specific novel."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM glossary_entries WHERE novel_id = ?",
                (novel_id,)
            )
            return cursor.rowcount

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_all_entries(
        self,
        novel_id: Optional[str] = None,
        include_global: bool = True,
        category: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[GlossaryEntryDB]:
        """
        Get all glossary entries with filtering.

        Args:
            novel_id: Filter by novel ID
            include_global: Include global entries (novel_id is NULL)
            category: Filter by category
            limit: Maximum entries to return
            offset: Offset for pagination

        Returns:
            List of glossary entries
        """
        conditions = []
        params = []

        if novel_id:
            if include_global:
                conditions.append("(novel_id = ? OR novel_id IS NULL)")
            else:
                conditions.append("novel_id = ?")
            params.append(novel_id)
        elif not include_global:
            conditions.append("novel_id IS NOT NULL")

        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM glossary_entries
                WHERE {where_clause}
                ORDER BY priority DESC, source
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset)
            ).fetchall()

            return [self._row_to_entry(row) for row in rows]

    def search_entries(
        self,
        query: str,
        search_target: bool = True,
        novel_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GlossaryEntryDB]:
        """
        Search entries by source or target text.

        Args:
            query: Search query
            search_target: Also search in target text
            novel_id: Filter by novel ID
            limit: Maximum results

        Returns:
            List of matching entries
        """
        with self._get_connection() as conn:
            if search_target:
                sql = """
                    SELECT * FROM glossary_entries
                    WHERE (source LIKE ? OR target LIKE ?)
                """
                params = [f"%{query}%", f"%{query}%"]
            else:
                sql = "SELECT * FROM glossary_entries WHERE source LIKE ?"
                params = [f"%{query}%"]

            if novel_id:
                sql += " AND (novel_id = ? OR novel_id IS NULL)"
                params.append(novel_id)

            sql += " ORDER BY priority DESC, source LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def get_entries_by_category(
        self,
        category: str,
        novel_id: Optional[str] = None,
    ) -> List[GlossaryEntryDB]:
        """Get all entries in a category."""
        return self.get_all_entries(novel_id=novel_id, category=category)

    def get_entries_by_tag(
        self,
        tag: str,
        novel_id: Optional[str] = None,
    ) -> List[GlossaryEntryDB]:
        """Get all entries with a specific tag."""
        with self._get_connection() as conn:
            sql = """
                SELECT * FROM glossary_entries
                WHERE tags LIKE ?
            """
            params = [f'%"{tag}"%']

            if novel_id:
                sql += " AND (novel_id = ? OR novel_id IS NULL)"
                params.append(novel_id)

            sql += " ORDER BY priority DESC, source"

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def count_entries(self, novel_id: Optional[str] = None) -> int:
        """Get total count of entries."""
        with self._get_connection() as conn:
            if novel_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM glossary_entries WHERE novel_id = ? OR novel_id IS NULL",
                    (novel_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM glossary_entries"
                ).fetchone()
            return row[0]

    # =========================================================================
    # Category Management
    # =========================================================================

    def get_categories(self) -> List[Dict]:
        """Get all categories."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM glossary_categories ORDER BY name"
            ).fetchall()
            return [dict(row) for row in rows]

    def add_category(self, name: str, description: str = "", color: str = "#808080") -> int:
        """Add a new category."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO glossary_categories (name, description, color) VALUES (?, ?, ?)",
                (name, description, color)
            )
            return cursor.lastrowid

    def delete_category(self, name: str) -> bool:
        """Delete a category (entries will keep their category string)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM glossary_categories WHERE name = ? AND name != 'general'",
                (name,)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Novel Management
    # =========================================================================

    def register_novel(self, novel_id: str, title: str, source_url: Optional[str] = None):
        """Register a novel for tracking."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO novels (id, title, source_url)
                VALUES (?, ?, ?)
                """,
                (novel_id, title, source_url)
            )

    def get_novels(self) -> List[Dict]:
        """Get all registered novels."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM novels ORDER BY title"
            ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Usage Tracking
    # =========================================================================

    def record_usage(self, entry_id: int, context: Optional[str] = None, novel_id: Optional[str] = None):
        """Record usage of a glossary entry."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO glossary_usage (entry_id, context, novel_id) VALUES (?, ?, ?)",
                (entry_id, context, novel_id)
            )
            conn.execute(
                "UPDATE glossary_entries SET usage_count = usage_count + 1 WHERE id = ?",
                (entry_id,)
            )

    def get_usage_stats(self, entry_id: int) -> Dict:
        """Get usage statistics for an entry."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_uses,
                    MIN(used_at) as first_used,
                    MAX(used_at) as last_used
                FROM glossary_usage
                WHERE entry_id = ?
                """,
                (entry_id,)
            ).fetchone()
            return dict(row) if row else {}

    # =========================================================================
    # Import/Export
    # =========================================================================

    def export_to_csv(self, path: Union[str, Path], novel_id: Optional[str] = None):
        """Export glossary to CSV file."""
        entries = self.get_all_entries(novel_id=novel_id)
        path = Path(path)

        with path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Source', 'Target', 'Case Sensitive', 'Word Boundary',
                'Notes', 'Category', 'Tags', 'Priority'
            ])
            for entry in entries:
                writer.writerow([
                    entry.source,
                    entry.target,
                    str(entry.case_sensitive),
                    str(entry.word_boundary),
                    entry.notes,
                    entry.category,
                    ','.join(entry.tags),
                    entry.priority,
                ])

    def export_to_json(self, path: Union[str, Path], novel_id: Optional[str] = None):
        """Export glossary to JSON file."""
        entries = self.get_all_entries(novel_id=novel_id)
        path = Path(path)

        data = [
            {
                'source': e.source,
                'target': e.target,
                'case_sensitive': e.case_sensitive,
                'word_boundary': e.word_boundary,
                'notes': e.notes,
                'category': e.category,
                'tags': e.tags,
                'priority': e.priority,
            }
            for e in entries
        ]

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def import_from_csv(
        self,
        path: Union[str, Path],
        novel_id: Optional[str] = None,
        replace: bool = False,
    ) -> int:
        """
        Import glossary from CSV file.

        Args:
            path: Path to CSV file
            novel_id: Assign entries to this novel
            replace: Replace existing entries with same source

        Returns:
            Number of entries imported
        """
        path = Path(path)
        entries = []

        with path.open('r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header

            for row in reader:
                if len(row) < 2:
                    continue

                entry = GlossaryEntryDB(
                    source=row[0].strip(),
                    target=row[1].strip(),
                    case_sensitive=row[2].lower() == 'true' if len(row) > 2 else True,
                    word_boundary=row[3].lower() == 'true' if len(row) > 3 else False,
                    notes=row[4] if len(row) > 4 else '',
                    category=row[5] if len(row) > 5 else 'general',
                    tags=row[6].split(',') if len(row) > 6 and row[6] else [],
                    priority=int(row[7]) if len(row) > 7 and row[7] else 0,
                    novel_id=novel_id,
                )
                entries.append(entry)

        return self.add_entries(entries)

    def import_from_json(
        self,
        path: Union[str, Path],
        novel_id: Optional[str] = None,
        replace: bool = False,
    ) -> int:
        """Import glossary from JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding='utf-8'))

        entries = []
        for item in data:
            entry = GlossaryEntryDB(
                source=item.get('source', ''),
                target=item.get('target', ''),
                case_sensitive=item.get('case_sensitive', True),
                word_boundary=item.get('word_boundary', False),
                notes=item.get('notes', ''),
                category=item.get('category', 'general'),
                tags=item.get('tags', []),
                priority=item.get('priority', 0),
                novel_id=novel_id,
            )
            entries.append(entry)

        return self.add_entries(entries)

    # =========================================================================
    # Text Processing
    # =========================================================================

    def apply_glossary_to_text(
        self,
        text: str,
        novel_id: Optional[str] = None,
        track_usage: bool = False,
    ) -> str:
        """
        Apply glossary replacements to text.

        Args:
            text: Text to process
            novel_id: Use novel-specific entries
            track_usage: Track which entries were used

        Returns:
            Text with replacements applied
        """
        entries = self.get_all_entries(novel_id=novel_id, include_global=True)

        # Convert to simple GlossaryEntry for apply_glossary
        simple_entries = [
            GlossaryEntry(
                source=e.source,
                target=e.target,
                case_sensitive=e.case_sensitive,
                word_boundary=e.word_boundary,
                notes=e.notes,
            )
            for e in entries
        ]

        result = apply_glossary(text, simple_entries)

        # Track usage if requested
        if track_usage:
            for entry in entries:
                if entry.source in text:
                    self.record_usage(entry.id, context=text[:100], novel_id=novel_id)

        return result

    def get_glossary_dict(self, novel_id: Optional[str] = None) -> Dict[str, str]:
        """Get glossary as simple dict (for translation providers that support it)."""
        entries = self.get_all_entries(novel_id=novel_id)
        return {e.source: e.target for e in entries}

    # =========================================================================
    # Helpers
    # =========================================================================

    def _row_to_entry(self, row: sqlite3.Row) -> GlossaryEntryDB:
        """Convert database row to GlossaryEntryDB."""
        return GlossaryEntryDB(
            id=row['id'],
            source=row['source'],
            target=row['target'],
            case_sensitive=bool(row['case_sensitive']),
            word_boundary=bool(row['word_boundary']),
            notes=row['notes'] or '',
            category=row['category'] or 'general',
            tags=json.loads(row['tags'] or '[]'),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            usage_count=row['usage_count'] or 0,
            novel_id=row['novel_id'],
            priority=row['priority'] or 0,
        )


# Singleton instance
_db_instance: Optional[GlossaryDB] = None


def get_glossary_db(db_path: Optional[Union[str, Path]] = None) -> GlossaryDB:
    """Get the glossary database instance."""
    global _db_instance
    if _db_instance is None or db_path:
        _db_instance = GlossaryDB(db_path or "~/.sagemtl/glossary.db")
    return _db_instance
