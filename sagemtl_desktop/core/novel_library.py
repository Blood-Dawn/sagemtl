"""
Novel Library - Persistent storage for fetched novels.

This module handles saving and loading crawled novels so they persist
between application sessions.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class SavedChapter:
    """A saved chapter in the library"""
    chapter_id: str
    chapter_number: int
    title: str
    content: str  # Original content
    cleaned_content: str = ""  # After cleaning/processing
    translated_content: str = ""  # After translation
    url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SavedChapter':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class SavedNovel:
    """A saved novel in the library"""
    novel_id: str
    title: str
    author: str
    source_url: str
    chapters: List[SavedChapter] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    cover_url: str = ""
    description: str = ""
    title_locked: bool = False  # Set when user manually renames a title.
    
    # Status tracking
    total_chapters: int = 0
    downloaded_chapters: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        self.total_chapters = len(self.chapters)
        self.downloaded_chapters = len(self.chapters)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'novel_id': self.novel_id,
            'title': self.title,
            'author': self.author,
            'source_url': self.source_url,
            'chapters': [ch.to_dict() for ch in self.chapters],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'cover_url': self.cover_url,
            'description': self.description,
            'title_locked': self.title_locked,
            'total_chapters': self.total_chapters,
            'downloaded_chapters': self.downloaded_chapters,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SavedNovel':
        """Create from dictionary"""
        chapters = [SavedChapter.from_dict(ch) for ch in data.get('chapters', [])]
        return cls(
            novel_id=data['novel_id'],
            title=data['title'],
            author=data.get('author', 'Unknown'),
            source_url=data.get('source_url', ''),
            chapters=chapters,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            cover_url=data.get('cover_url', ''),
            description=data.get('description', ''),
            title_locked=bool(data.get('title_locked', False)),
            total_chapters=data.get('total_chapters', len(chapters)),
            downloaded_chapters=data.get('downloaded_chapters', len(chapters)),
        )
    
    def get_chapter(self, chapter_id: str) -> Optional[SavedChapter]:
        """Get a chapter by ID"""
        return next((ch for ch in self.chapters if ch.chapter_id == chapter_id), None)
    
    def get_chapter_by_number(self, chapter_number: int) -> Optional[SavedChapter]:
        """Get a chapter by number"""
        return next((ch for ch in self.chapters if ch.chapter_number == chapter_number), None)


class NovelLibrary:
    """
    Manages persistent storage of fetched novels.
    
    Stores novels in JSON format in the user's app data directory.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the library.
        
        Args:
            storage_path: Optional custom path for storage directory
        """
        if storage_path:
            self.storage_dir = Path(storage_path)
        else:
            # Default to user's app data
            self.storage_dir = self._get_default_storage_path()
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.library_file = self.storage_dir / "novel_library.json"
        self.novels_dir = self.storage_dir / "novels"
        self.novels_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._novels: Dict[str, SavedNovel] = {}
        
        # Load existing library
        self._load_library()
    
    def _get_default_storage_path(self) -> Path:
        """Get default storage path based on OS"""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('APPDATA', '~'))
        else:  # Unix/Linux/Mac
            base = Path.home() / '.local' / 'share'
        
        return base / 'SageMTL' / 'library'
    
    def _load_library(self):
        """Load the library index from disk"""
        if not self.library_file.exists():
            self._novels = {}
            return
        
        try:
            with open(self.library_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._novels = {}
            for novel_data in data.get('novels', []):
                novel = SavedNovel.from_dict(novel_data)
                self._novels[novel.novel_id] = novel
        except json.JSONDecodeError as e:
            print(f"Warning: Library file is corrupted: {e}")
            print("Creating backup and starting fresh library...")
            # Backup the corrupted file
            backup_path = self.library_file.with_suffix('.json.corrupted')
            import contextlib
            with contextlib.suppress(Exception):
                import shutil
                shutil.copy2(self.library_file, backup_path)
                print(f"Backup saved to: {backup_path}")
            # Start fresh
            self._novels = {}
            self._save_library()  # Create a new valid library file
        except Exception as e:
            print(f"Warning: Failed to load library: {e}")
            self._novels = {}
    
    def _save_library(self):
        """Save the library index to disk"""
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'novels': [novel.to_dict() for novel in self._novels.values()]
        }
        
        try:
            with open(self.library_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save library: {e}")
    
    def add_novel(self, title: str, author: str, source_url: str,
                  chapters: List[Dict[str, Any]]) -> SavedNovel:
        """
        Add a new novel to the library.
        
        Args:
            title: Novel title
            author: Author name
            source_url: Original URL
            chapters: List of chapter dicts with title, content, chapter_number, url
            
        Returns:
            The created SavedNovel
        """
        novel_id = str(uuid.uuid4())[:8]
        
        # Create chapter objects
        saved_chapters = []
        for idx, ch in enumerate(chapters):
            chapter = SavedChapter(
                chapter_id=str(uuid.uuid4())[:8],
                chapter_number=ch.get('chapter_number', idx + 1),
                title=ch.get('title', f'Chapter {idx + 1}'),
                content=ch.get('content', ''),
                url=ch.get('url', '')
            )
            saved_chapters.append(chapter)
        
        novel = SavedNovel(
            novel_id=novel_id,
            title=title,
            author=author or 'Unknown',
            source_url=source_url,
            chapters=saved_chapters
        )
        
        self._novels[novel_id] = novel
        self._save_library()
        
        return novel
    
    def add_novel_from_crawled(self, crawled_novel, source_url: str) -> SavedNovel:
        """
        Add a novel from a CrawledNovel object.
        
        Args:
            crawled_novel: CrawledNovel instance
            source_url: The source URL
            
        Returns:
            The created SavedNovel
        """
        chapters = [
            {
                'title': ch.title,
                'content': ch.content,
                'chapter_number': ch.chapter_number,
                'url': getattr(ch, 'url', '')
            }
            for ch in crawled_novel.chapters
        ]
        
        return self.add_novel(
            title=crawled_novel.title,
            author=crawled_novel.author or 'Unknown',
            source_url=source_url,
            chapters=chapters
        )

    @staticmethod
    def _chapter_identity(url: str, title: str, chapter_number: Optional[int]) -> str:
        """
        Build a stable identity for chapter merge operations.
        """
        if url:
            return f"url:{url.strip()}"
        normalized_title = (title or "").strip().lower()
        if chapter_number is not None:
            return f"num:{chapter_number}:{normalized_title}"
        return f"title:{normalized_title}"

    def upsert_novel_from_crawled(
        self,
        crawled_novel,
        source_url: str,
        resume_existing: bool = False
    ) -> SavedNovel:
        """
        Add or merge a crawled novel by source URL.

        Args:
            crawled_novel: CrawledNovel instance
            source_url: The source URL
            resume_existing: If True, merge chapters into existing novel if URL matches
        """
        existing = self.get_novel_by_url(source_url) if resume_existing else None
        if not existing:
            return self.add_novel_from_crawled(crawled_novel, source_url)

        existing_index: Dict[str, SavedChapter] = {}
        for chapter in existing.chapters:
            identity = self._chapter_identity(chapter.url, chapter.title, chapter.chapter_number)
            existing_index[identity] = chapter

        for crawled_chapter in crawled_novel.chapters:
            chapter_number = crawled_chapter.chapter_number
            if chapter_number is None:
                chapter_number = len(existing.chapters) + 1

            identity = self._chapter_identity(
                getattr(crawled_chapter, "url", ""),
                crawled_chapter.title,
                chapter_number
            )

            if identity in existing_index:
                target = existing_index[identity]
                if crawled_chapter.content:
                    target.content = crawled_chapter.content
                if getattr(crawled_chapter, "url", ""):
                    target.url = crawled_chapter.url
                if crawled_chapter.title:
                    target.title = crawled_chapter.title
                if chapter_number:
                    target.chapter_number = chapter_number
                continue

            new_chapter = SavedChapter(
                chapter_id=str(uuid.uuid4())[:8],
                chapter_number=chapter_number,
                title=crawled_chapter.title,
                content=crawled_chapter.content,
                url=getattr(crawled_chapter, "url", ""),
            )
            existing.chapters.append(new_chapter)
            existing_index[identity] = new_chapter

        existing.chapters.sort(
            key=lambda chapter: (chapter.chapter_number or 0, (chapter.title or "").lower())
        )
        if not existing.title_locked:
            existing.title = crawled_novel.title or existing.title
        existing.author = crawled_novel.author or existing.author
        existing.total_chapters = len(existing.chapters)
        existing.downloaded_chapters = len([chapter for chapter in existing.chapters if chapter.content.strip()])

        self.update_novel(existing)
        return existing
    
    def get_novel(self, novel_id: str) -> Optional[SavedNovel]:
        """Get a novel by ID"""
        return self._novels.get(novel_id)
    
    def get_novel_by_url(self, source_url: str) -> Optional[SavedNovel]:
        """Get a novel by its source URL"""
        return next((novel for novel in self._novels.values() if novel.source_url == source_url), None)
    
    def get_all_novels(self) -> List[SavedNovel]:
        """Get all novels in the library"""
        return list(self._novels.values())
    
    def remove_novel(self, novel_id: str) -> bool:
        """
        Remove a novel from the library.
        
        Args:
            novel_id: ID of the novel to remove
            
        Returns:
            True if removed, False if not found
        """
        if novel_id in self._novels:
            del self._novels[novel_id]
            self._save_library()
            return True
        return False
    
    def update_novel(self, novel: SavedNovel):
        """
        Update a novel in the library.
        
        Args:
            novel: Updated SavedNovel
        """
        novel.updated_at = datetime.now().isoformat()
        self._novels[novel.novel_id] = novel
        self._save_library()
    
    def update_chapter_content(self, novel_id: str, chapter_id: str,
                               cleaned_content: str = None,
                               translated_content: str = None):
        """
        Update processed content for a chapter.
        
        Args:
            novel_id: ID of the novel
            chapter_id: ID of the chapter
            cleaned_content: Cleaned text
            translated_content: Translated text
        """
        novel = self._novels.get(novel_id)
        if not novel:
            return
        
        chapter = novel.get_chapter(chapter_id)
        if not chapter:
            return
        
        if cleaned_content is not None:
            chapter.cleaned_content = cleaned_content
        if translated_content is not None:
            chapter.translated_content = translated_content
        
        novel.updated_at = datetime.now().isoformat()
        self._save_library()
    
    def clear_library(self):
        """Clear all novels from the library"""
        self._novels.clear()
        self._save_library()
    
    @property
    def novel_count(self) -> int:
        """Get the number of novels in the library"""
        return len(self._novels)
