"""
Main entry point for SageMTL Desktop Application.
"""

import os
import sys
import warnings
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

try:  # frozen builds run this file as __main__, which has no package context
    from .ui.main_window import MainWindow
except ImportError:  # pragma: no cover - exercised only in packaged builds
    from sagemtl_desktop.ui.main_window import MainWindow

# Suppress deprecated pkg_resources warning from ctranslate2
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*')


def _run_selftest() -> int:
    """Import the full heavy manga stack to validate a packaged (frozen) build.

    Triggered by SAGEMTL_SELFTEST=1 so a windowed build (no console) can be
    verified headlessly: every heavy third-party library and every manga module
    is imported, results are written to SAGEMTL_SELFTEST_LOG (if set), and the
    process exits 0 only when all imports succeed. Inert during normal use.
    """
    import importlib

    heavy = [
        "numpy", "PIL", "cv2", "shapely",
        "torch", "onnxruntime",
        "transformers", "tokenizers", "sentencepiece",
        "huggingface_hub", "safetensors",
        "manga_ocr", "jaconv", "fugashi", "unidic_lite",
        "paddle", "paddleocr", "paddlex",
    ]
    manga_mods = [
        "sagemtl_desktop.core.manga.pipeline",
        "sagemtl_desktop.core.manga.detect",
        "sagemtl_desktop.core.manga.ocr",
        "sagemtl_desktop.core.manga.translate",
        "sagemtl_desktop.core.manga.providers",
        "sagemtl_desktop.core.manga.inpaint",
        "sagemtl_desktop.core.manga.typeset",
        "sagemtl_desktop.core.manga.webtoon",
        "sagemtl_desktop.core.manga.studio",
        "sagemtl_desktop.core.manga.model_registry",
        "sagemtl_desktop.core.manga.library",
        "sagemtl_desktop.core.manga.exporter",
        "sagemtl_manga_crawler.core.registry",
        "sagemtl_manga_crawler.sources.mangadex",
        "sagemtl_manga_crawler.sources.suwayomi",
    ]
    lines = []
    failures = []
    for name in heavy + manga_mods:
        try:
            importlib.import_module(name)
            lines.append(f"  [OK]  {name}")
        except Exception as exc:  # noqa: BLE001 - report every import failure
            lines.append(f"  [FAIL] {name}: {exc!r}")
            failures.append(name)
    lines.append(
        f"SELFTEST FAILED: {failures}" if failures
        else f"SELFTEST PASSED: {len(heavy) + len(manga_mods)} imports OK"
    )
    out = "\n".join(lines)
    log_path = os.environ.get("SAGEMTL_SELFTEST_LOG")
    if log_path:
        try:
            Path(log_path).write_text(out + "\n", encoding="utf-8")
        except Exception:
            pass
    print(out)
    return 1 if failures else 0


def main():
    """Main entry point"""
    if os.environ.get("SAGEMTL_SELFTEST") == "1":
        sys.exit(_run_selftest())

    # Note: AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps are deprecated in Qt6
    # High DPI scaling is enabled by default in Qt6, no need to set attributes

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("SageMTL Desktop")
    app.setOrganizationName("SageMTL")
    app.setOrganizationDomain("sagemtl.app")

    # Set application icon
    icon_path = Path(__file__).parent / "resources" / "icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
