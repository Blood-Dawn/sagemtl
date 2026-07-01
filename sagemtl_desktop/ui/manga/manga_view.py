"""Main manga workspace: series list + chapter selector + reader.

Thin UI: it builds JobManager jobs whose processors call the Qt-free
``core.manga.jobs`` functions (which drive the crawler, pipeline, and library).
The view never holds business logic. See spec section 11.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from sagemtl_desktop.core.manga import jobs as manga_jobs
from sagemtl_desktop.core.models import JobType

from ..i18n import tr
from .reader_widget import ReaderWidget


class MangaView(QWidget):
    """Series list + chapter selector + before/after reader."""

    def __init__(
        self,
        job_manager,
        library,
        config_provider: Callable[[], object],
        glossary=None,
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._jm = job_manager
        self._library = library
        self._config_provider = config_provider
        self._glossary = glossary
        self._language = language
        self._build_ui()
        self.refresh_series()

    def _tr(self, key: str) -> str:
        return tr(self._language, key)

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel(self._tr("manga.series_list.title")))
        self._series_list = QListWidget()
        self._series_list.currentRowChanged.connect(self._on_series_selected)
        lv.addWidget(self._series_list, stretch=1)

        self._chapter_combo = QComboBox()
        lv.addWidget(self._chapter_combo)

        self._add_btn = QPushButton(self._tr("action.manga_add_url"))
        self._add_btn.clicked.connect(self.add_series_by_url)
        lv.addWidget(self._add_btn)

        self._translate_btn = QPushButton(self._tr("action.manga_translate"))
        self._translate_btn.clicked.connect(self.translate_selected_chapter)
        lv.addWidget(self._translate_btn)

        self._studio_btn = QPushButton(self._tr("action.manga_studio"))
        self._studio_btn.clicked.connect(self.open_studio)
        lv.addWidget(self._studio_btn)

        self._export_btn = QPushButton(self._tr("action.manga_export"))
        self._export_btn.clicked.connect(self.export_selected_chapter)
        lv.addWidget(self._export_btn)

        splitter.addWidget(left)
        self._reader = ReaderWidget(self._language)
        splitter.addWidget(self._reader)
        splitter.setSizes([280, 720])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    # -- data binding -------------------------------------------------------

    def refresh_series(self) -> None:
        self._series_list.clear()
        for series in self._library.get_all_series():
            label = series.title or series.source_url or series.series_id
            self._series_list.addItem(label)
        if self._series_list.count() and self._series_list.currentRow() < 0:
            self._series_list.setCurrentRow(0)

    def _selected_series(self):
        row = self._series_list.currentRow()
        all_series = self._library.get_all_series()
        if 0 <= row < len(all_series):
            return all_series[row]
        return None

    def _on_series_selected(self, row: int) -> None:
        self._chapter_combo.clear()
        series = self._selected_series()
        if series is None:
            return
        for chapter in series.chapters:
            self._chapter_combo.addItem(
                chapter.number and f"Ch {chapter.number} {chapter.title}".strip() or (chapter.title or chapter.chapter_id),
                chapter.chapter_id,
            )
        self._load_reader_for_selection()

    def _selected_chapter_id(self) -> Optional[str]:
        if self._chapter_combo.currentIndex() < 0:
            return None
        return self._chapter_combo.currentData()

    def _load_reader_for_selection(self) -> None:
        series = self._selected_series()
        chapter_id = self._selected_chapter_id()
        if series is None or chapter_id is None:
            self._reader.clear()
            return
        chapter = next((c for c in series.chapters if c.chapter_id == chapter_id), None)
        if chapter is None or not chapter.pages:
            self._reader.clear()
            return
        pages = []
        for page in sorted(chapter.pages, key=lambda p: p.index):
            pages.append({
                "raw": _read_bytes(page.source_image_path),
                "rendered": _read_bytes(page.rendered_image_path),
                "regions": page.regions,
                "status": page.status,
            })
        self._reader.set_pages(pages)

    # -- actions (wired to jobs) -------------------------------------------

    def _run_job(self, job_type, name: str, work, on_done=None) -> str:
        job_id = self._jm.create_job(job_type, name)

        def processor(job, progress, log):
            work(progress, lambda message: log("info", message))

        def on_update(updated_id: str) -> None:
            if updated_id != job_id:
                return
            job = self._jm.get_job(job_id)
            if job is None or job.status.name not in ("COMPLETED", "FAILED"):
                return
            try:
                self._jm.job_updated.disconnect(on_update)
            except (RuntimeError, TypeError):
                pass
            if job.status.name == "COMPLETED" and on_done is not None:
                on_done()

        self._jm.job_updated.connect(on_update)
        self._jm.start_job(job_id, processor)
        return job_id

    def add_series_by_url(self) -> None:
        url, ok = QInputDialog.getText(self, self._tr("action.manga_add_url"), "URL:")
        if not ok or not url.strip():
            return
        url = url.strip()

        def work(progress, log):
            source = _mangadex_source()
            manga_jobs.add_series_from_url(self._library, source, url, log_cb=log)

        self._run_job(JobType.MANGA_CRAWL, f"Add {url}", work, on_done=self.refresh_series)

    def translate_selected_chapter(self) -> None:
        series = self._selected_series()
        chapter_id = self._selected_chapter_id()
        if series is None or chapter_id is None:
            return
        config = self._config_provider()
        series_id = series.series_id
        source_name = series.source_name or "mangadex"

        def work(progress, log):
            from sagemtl_manga_crawler.core.registry import build_source

            source = build_source(source_name, config)
            pipeline = _build_pipeline(config, self._glossary)
            manga_jobs.translate_chapter(
                self._library, source, pipeline, series_id, chapter_id,
                source_lang=getattr(config, "source_lang", "auto"),
                progress_cb=progress, log_cb=log,
            )

        self._run_job(
            JobType.MANGA_TRANSLATE, f"Translate {series.title}",
            work, on_done=self._load_reader_for_selection,
        )

    def export_selected_chapter(self) -> None:
        series = self._selected_series()
        chapter_id = self._selected_chapter_id()
        if series is None or chapter_id is None:
            return
        from ..export_dialog import ExportDialog

        dialog = ExportDialog(self, manga=True)
        if dialog.exec() != QDialog.Accepted:
            return
        fmt = dialog.get_format()
        if fmt == "folder":
            dest = QFileDialog.getExistingDirectory(self, self._tr("action.manga_export"))
        else:
            dest, _ = QFileDialog.getSaveFileName(
                self, self._tr("action.manga_export"), f"chapter.{fmt}", f"{fmt.upper()} (*.{fmt})"
            )
        if not dest:
            return
        series_id = series.series_id

        def work(progress, log):
            manga_jobs.export_chapter(self._library, series_id, chapter_id, Path(dest), fmt=fmt, log_cb=log)

        self._run_job(JobType.MANGA_EXPORT, f"Export {series.title}", work)

    def open_studio(self) -> None:
        """Open the Studio editor on the page currently shown in the reader."""
        from sagemtl_desktop.core.manga.detect import load_image_rgb
        from sagemtl_desktop.core.manga.models import TextRegion
        from sagemtl_desktop.core.manga.studio import StudioModel
        from .studio import StudioWindow

        series = self._selected_series()
        chapter_id = self._selected_chapter_id()
        if series is None or chapter_id is None:
            return
        chapter = next((c for c in series.chapters if c.chapter_id == chapter_id), None)
        if chapter is None or not chapter.pages:
            return
        pages = sorted(chapter.pages, key=lambda p: p.index)
        idx = max(0, min(self._reader.current_index(), len(pages) - 1))
        page = pages[idx]

        clean_bytes = _read_bytes(page.clean_image_path) or _read_bytes(page.source_image_path)
        if not clean_bytes:
            return
        base = load_image_rgb(clean_bytes)
        regions = [TextRegion.from_dict(r) for r in page.regions]
        config = self._config_provider()
        model = StudioModel.from_regions(
            base, regions, default_font=getattr(config, "font_path", None)
        )

        def on_save(data: bytes) -> None:
            self._save_studio_result(series.series_id, chapter_id, page, data)

        window = StudioWindow(model, on_save=on_save, language=self._language, parent=self)
        window.exec()

    def _save_studio_result(self, series_id: str, chapter_id: str, page, data: bytes) -> None:
        series = self._library.get_series(series_id)
        if series is None:
            return
        out = self._library.save_page_image(series_id, chapter_id, page.index, data, ext="png", kind="out")
        page.rendered_image_path = str(out)
        page.status = "edited"
        self._library.update_series(series)
        self._load_reader_for_selection()


def _read_bytes(path: str) -> bytes:
    if path and Path(path).exists():
        return Path(path).read_bytes()
    return b""


def _mangadex_source():
    from sagemtl_manga_crawler.sources.mangadex import MangaDexSource

    return MangaDexSource()


def _build_pipeline(config, glossary):
    from sagemtl_desktop.core.manga.pipeline import MangaPipeline

    return MangaPipeline(config, glossary)
