"""Phase 8 UI tests: manga widgets construct + mode switch (offscreen Qt)."""

from __future__ import annotations

import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sagemtl_desktop.ui.i18n import tr  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _png(color=(200, 0, 0)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


# --- i18n (no Qt needed) ---


def test_manga_i18n_keys_present():
    for key in (
        "menu.manga", "mode.novels", "mode.manga",
        "action.manga_add_url", "action.manga_translate", "action.manga_export",
        "manga.reader.before", "manga.reader.after",
    ):
        assert tr("en", key) != key, f"missing en key {key}"
        assert tr("es", key) != key, f"missing es key {key}"
    # es differs from en for a translated label
    assert tr("es", "mode.novels") != tr("en", "mode.novels")


# --- widgets (offscreen) ---


def test_reader_widget_toggles_and_overlay(qapp):
    from sagemtl_desktop.ui.manga.reader_widget import ReaderWidget

    png = _png()
    reader = ReaderWidget(language="en")
    reader.set_pages([
        {"raw": png, "rendered": _png((0, 200, 0)), "regions": [{"box": [0, 0, 4, 4], "cls": "text_bubble"}], "status": "done"},
    ])
    reader._on_regions_toggled(True)   # draw region overlay
    reader._on_toggle(False)           # show "before"
    reader._on_toggle(True)            # show "after"
    reader.next_page()                 # single page -> stays
    assert reader._index == 0
    reader.clear()
    assert reader._current() is None


def test_manga_view_lists_series(qapp, tmp_path):
    from sagemtl_desktop.core.job_manager import JobManager
    from sagemtl_desktop.core.manga.library import MangaLibrary
    from sagemtl_desktop.core.manga.models import MangaConfig, MangaChapter, MangaSeries
    from sagemtl_desktop.ui.manga.manga_view import MangaView

    lib = MangaLibrary(tmp_path)
    lib.add_series(MangaSeries(
        series_id="s1", title="My Series", source_url="u",
        chapters=[MangaChapter(chapter_id="c1", number="1", title="One")],
    ))
    view = MangaView(JobManager(), lib, lambda: MangaConfig(), glossary=None, language="en")
    assert view._series_list.count() == 1
    view._series_list.setCurrentRow(0)
    assert view._selected_series().series_id == "s1"
    assert view._chapter_combo.count() == 1
    assert view._selected_chapter_id() == "c1"


def test_export_dialog_manga_mode(qapp):
    from sagemtl_desktop.ui.export_dialog import ExportDialog

    dialog = ExportDialog(manga=True)
    assert dialog.get_format() == "cbz"        # default
    dialog.pdf_radio.setChecked(True)
    assert dialog.get_format() == "pdf"
    dialog.folder_radio.setChecked(True)
    assert dialog.get_format() == "folder"

    # novel mode is unchanged
    novel = ExportDialog(manga=False)
    assert novel.get_format() == "txt"
    novel.epub_radio.setChecked(True)
    assert novel.get_format() == "epub"


def test_typeset_editor_edit_and_rerender(qapp):
    from sagemtl_desktop.core.manga.models import TextRegion
    from sagemtl_desktop.ui.manga.typeset_editor import TypesetEditor

    clean = _png((255, 255, 255))  # small white page
    region = TextRegion(box=(0, 0, 8, 8), cls="text_bubble", source_text="src", target_text="orig")
    editor = TypesetEditor(clean, [region], language="en")
    first = editor.get_rendered_bytes()
    assert first[:8] == b"\x89PNG\r\n\x1a\n"

    # edit the translation cell and re-render
    editor._table.item(0, 2).setText("changed text")
    editor._rerender()
    assert editor.get_regions()[0].target_text == "changed text"
    assert editor.get_rendered_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    # Nudge placement via the X/Y cells; box moves but keeps its size (8x8).
    editor._table.item(0, 3).setText("3")
    editor._table.item(0, 4).setText("5")
    editor._rerender()
    assert editor.get_regions()[0].box == (3, 5, 11, 13)


def test_studio_window_edits_and_saves(qapp):
    import numpy as np

    from sagemtl_desktop.core.manga.studio import StudioModel, TextLayer
    from sagemtl_desktop.ui.manga.studio import StudioWindow

    base = np.full((120, 160, 3), 255, np.uint8)
    model = StudioModel(base, layers=[TextLayer(text="Hi", x=10, y=10, width=80, height=30)])
    saved = {}
    window = StudioWindow(model, on_save=lambda data: saved.update(png=data), language="en")

    # tools + cleanup ops route to the model
    window.canvas.set_tool("erase")
    window.canvas.set_tool("select")
    window._add_text()
    assert len(model.layers) == 2
    window._reset_image()  # no crash

    # save composites text over the page and returns a valid PNG
    window.save()
    assert saved["png"][:8] == b"\x89PNG\r\n\x1a\n"


def test_mainwindow_manga_mode_switch(qapp):
    try:
        from sagemtl_desktop.ui.main_window import MainWindow

        win = MainWindow()
    except ImportError as exc:  # pragma: no cover - only an env dep gap may skip
        pytest.skip(f"MainWindow dependency unavailable: {exc}")
    # Any other construction error (Qt wiring, attribute regressions) must FAIL,
    # not silently skip -- this is the sole guard of the Novels<->Manga integration.
    try:
        win._switch_to_manga_mode()
        assert win._mode_stack.currentWidget() is win._manga_view
        win._switch_to_novel_mode()
        assert win._mode_stack.currentWidget() is win._novel_container
    finally:
        win.close()
