"""
Main entry point for SageMTL Desktop Application.
"""

import sys
import warnings
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from .ui.main_window import MainWindow

# Suppress deprecated pkg_resources warning from ctranslate2
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*')


def main():
    """Main entry point"""
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
