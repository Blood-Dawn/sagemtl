"""Library management for SageMTL.

This module provides:
- SQLite-based novel library
- Novel metadata storage
- Reading progress tracking
- Series grouping
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global library instance
_library: Optional["LibraryManager"] = None


@dataclass
class NovelEntry:
    """Entry in the novel library."""

    id: str
    title: str
    author: str = ""
    description: str = ""
    cover_path: Optional[str] = None
    source_url: Optional[str] = None

    # Content info
    total_chapters: int = 0
    downloaded_chapters: int = 0
    translated: bool = False

    # Reading progress
    last_read_chapter: int = 0
    read_chapters: List[int] = field(default_factory=list)

    # Metadata
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: str = "ongoing"  # ongoing, completed, hiatus

    # Series
    series_id: Optional[str] = None
    series_index: int = 0

    # Timestamps
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None

    # Storage paths
    data_path: Optional[str] = None
    export_paths: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "cover_path": self.cover_path,
            "source_url": self.source_url,
            "total_chapters": self.total_chapters,
            "downloaded_chapters": self.downloaded_chapters,
            "translated": self.translated,
            "last_read_chapter": self.last_read_chapter,
            "read_chapters": json.dumps(self.read_chapters),
            "genres": json.dumps(self.genres),
            "tags": json.dumps(self.tags),
            "status": self.status,
            "series_id": self.series_id,
            "series_index": self.series_index,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_read_at": self.last_read_at.isoformat() if self.last_read_at else None,
            "data_path": self.data_path,
            "export_paths": json.dumps(self.export_paths),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NovelEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            author=data.get("author", ""),
            description=data.get("description", ""),
            cover_path=data.get("cover_path"),
            source_url=data.get("source_url"),
            total_chapters=data.get("total_chapters", 0),
            downloaded_chapters=data.get("downloaded_chapters", 0),
            translated=data.get("translated", False),
            last_read_chapter=data.get("last_read_chapter", 0),
            read_chapters=json.loads(data.get("read_chapters", "[]")),
            genres=json.loads(data.get("genres", "[]")),
            tags=json.loads(data.get("tags", "[]")),
            status=data.get("status", "ongoing"),
            series_id=data.get("series_id"),
            series_index=data.get("series_index", 0),
            added_at=datetime.fromisoformat(data["added_at"]) if data.get("added_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            last_read_at=datetime.fromisoformat(data["last_read_at"]) if data.get("last_read_at") else None,
            data_path=data.get("data_path"),
            export_paths=json.loads(data.get("export_paths", "{}")),
        )

    @property
    def progress_percent(self) -> float:
        """Get reading progress percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (len(self.read_chapters) / self.total_chapters) * 100


@dataclass
class Series:
    """Series grouping for novels."""

    id: str
    title: str
    description: str = ""
    novels: List[str] = field(default_factory=list)  # Novel IDs


class LibraryManager:
    """Manages the novel library database.

    Usage:
        library = LibraryManager()
        library.add_novel(novel_entry)
        novels = library.get_all_novels()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the library manager.

        Args:
            db_path: Path to the SQLite database. If None, uses default location.
        """
        if db_path is None:
            db_path = self._get_default_db_path()

        self._db_path = db_path
        self._ensure_db()

    @staticmethod
    def _get_default_db_path() -> Path:
        """Get default database path."""
        # Use user's data directory
        import platform
        if platform.system() == "Windows":
            base = Path.home() / "AppData" / "Roaming" / "SageMTL"
        elif platform.system() == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "SageMTL"
        else:
            base = Path.home() / ".local" / "share" / "sagemtl"

        base.mkdir(parents=True, exist_ok=True)
        return base / "library.db"

    def _ensure_db(self) -> None:
        """Ensure database exists with correct schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS novels (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    description TEXT,
                    cover_path TEXT,
                    source_url TEXT,
                    total_chapters INTEGER DEFAULT 0,
                    downloaded_chapters INTEGER DEFAULT 0,
                    translated INTEGER DEFAULT 0,
                    last_read_chapter INTEGER DEFAULT 0,
                    read_chapters TEXT DEFAULT '[]',
                    genres TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'ongoing',
                    series_id TEXT,
                    series_index INTEGER DEFAULT 0,
                    added_at TEXT,
                    updated_at TEXT,
                    last_read_at TEXT,
                    data_path TEXT,
                    export_paths TEXT DEFAULT '{}'
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS series (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT
                )
            """)

            # Create indices
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_novels_title ON novels(title)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_novels_author ON novels(author)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_novels_series ON novels(series_id)
            """)

            conn.commit()

    def add_novel(self, novel: NovelEntry) -> None:
        """Add a novel to the library."""
        if novel.added_at is None:
            novel.added_at = datetime.now()
        novel.updated_at = datetime.now()

        with sqlite3.connect(self._db_path) as conn:
            data = novel.to_dict()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = list(data.values())

            conn.execute(
                f"INSERT OR REPLACE INTO novels ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()

    def get_novel(self, novel_id: str) -> Optional[NovelEntry]:
        """Get a novel by ID."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM novels WHERE id = ?",
                (novel_id,),
            )
            row = cursor.fetchone()

            if row:
                return NovelEntry.from_dict(dict(row))
            return None

    def get_all_novels(
        self,
        sort_by: str = "title",
        descending: bool = False,
    ) -> List[NovelEntry]:
        """Get all novels in the library."""
        valid_sort = ["title", "author", "added_at", "updated_at", "last_read_at"]
        if sort_by not in valid_sort:
            sort_by = "title"

        order = "DESC" if descending else "ASC"

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM novels ORDER BY {sort_by} {order}"
            )

            return [NovelEntry.from_dict(dict(row)) for row in cursor.fetchall()]

    def search_novels(
        self,
        query: str,
        fields: Optional[List[str]] = None,
    ) -> List[NovelEntry]:
        """Search novels by query."""
        if fields is None:
            fields = ["title", "author", "description"]

        conditions = " OR ".join([f"{field} LIKE ?" for field in fields])
        params = [f"%{query}%" for _ in fields]

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM novels WHERE {conditions}",
                params,
            )

            return [NovelEntry.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_novel(self, novel_id: str, **updates) -> bool:
        """Update a novel's fields."""
        novel = self.get_novel(novel_id)
        if not novel:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(novel, key):
                setattr(novel, key, value)

        novel.updated_at = datetime.now()
        self.add_novel(novel)
        return True

    def delete_novel(self, novel_id: str) -> bool:
        """Delete a novel from the library."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM novels WHERE id = ?",
                (novel_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def mark_chapter_read(self, novel_id: str, chapter: int) -> None:
        """Mark a chapter as read."""
        novel = self.get_novel(novel_id)
        if novel:
            if chapter not in novel.read_chapters:
                novel.read_chapters.append(chapter)
                novel.read_chapters.sort()
            novel.last_read_chapter = max(novel.last_read_chapter, chapter)
            novel.last_read_at = datetime.now()
            self.add_novel(novel)

    def get_reading_progress(self, novel_id: str) -> Dict[str, Any]:
        """Get reading progress for a novel."""
        novel = self.get_novel(novel_id)
        if not novel:
            return {}

        return {
            "total_chapters": novel.total_chapters,
            "read_chapters": len(novel.read_chapters),
            "last_read_chapter": novel.last_read_chapter,
            "progress_percent": novel.progress_percent,
            "last_read_at": novel.last_read_at,
        }

    # Series management

    def add_series(self, series: Series) -> None:
        """Add a series."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO series (id, title, description) VALUES (?, ?, ?)",
                (series.id, series.title, series.description),
            )
            conn.commit()

    def get_series(self, series_id: str) -> Optional[Series]:
        """Get a series by ID."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM series WHERE id = ?",
                (series_id,),
            )
            row = cursor.fetchone()

            if row:
                series = Series(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"] or "",
                )
                # Get novels in series
                novels_cursor = conn.execute(
                    "SELECT id FROM novels WHERE series_id = ? ORDER BY series_index",
                    (series_id,),
                )
                series.novels = [r["id"] for r in novels_cursor.fetchall()]
                return series
            return None

    def get_novels_in_series(self, series_id: str) -> List[NovelEntry]:
        """Get all novels in a series."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM novels WHERE series_id = ? ORDER BY series_index",
                (series_id,),
            )

            return [NovelEntry.from_dict(dict(row)) for row in cursor.fetchall()]

    # Statistics

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row

            total_novels = conn.execute("SELECT COUNT(*) as count FROM novels").fetchone()["count"]
            total_chapters = conn.execute("SELECT SUM(total_chapters) as total FROM novels").fetchone()["total"] or 0
            downloaded = conn.execute("SELECT SUM(downloaded_chapters) as total FROM novels").fetchone()["total"] or 0
            translated = conn.execute("SELECT COUNT(*) as count FROM novels WHERE translated = 1").fetchone()["count"]

            # Genre distribution
            genres_cursor = conn.execute("SELECT genres FROM novels")
            genre_counts: Dict[str, int] = {}
            for row in genres_cursor:
                for genre in json.loads(row["genres"]):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

            return {
                "total_novels": total_novels,
                "total_chapters": total_chapters,
                "downloaded_chapters": downloaded,
                "translated_novels": translated,
                "top_genres": sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            }


def get_library(db_path: Optional[Path] = None) -> LibraryManager:
    """Get the global library manager instance."""
    global _library

    if _library is None or (db_path is not None and _library._db_path != db_path):
        _library = LibraryManager(db_path)

    return _library
