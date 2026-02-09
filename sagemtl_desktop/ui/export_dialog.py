"""
Export format selection dialog.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QRadioButton, QButtonGroup,
    QLineEdit, QDialogButtonBox, QGroupBox, QFormLayout
)


class ExportDialog(QDialog):
    """Dialog for selecting export format and options"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)

        self.txt_radio = QRadioButton("Text File (.txt)")
        self.txt_radio.setChecked(True)
        self.txt_radio.setToolTip("Export as plain text with headers")

        self.epub_radio = QRadioButton("EPUB eBook (.epub)")
        self.epub_radio.setToolTip("Export as EPUB eBook with chapters")

        self.format_group = QButtonGroup()
        self.format_group.addButton(self.txt_radio, 0)
        self.format_group.addButton(self.epub_radio, 1)

        format_layout.addWidget(self.txt_radio)
        format_layout.addWidget(self.epub_radio)

        layout.addWidget(format_group)

        # EPUB options (shown only when EPUB is selected)
        self.epub_options_group = QGroupBox("EPUB Options")
        epub_options_layout = QFormLayout(self.epub_options_group)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Unknown")
        epub_options_layout.addRow("Author:", self.author_input)

        layout.addWidget(self.epub_options_group)

        # Initially hide EPUB options
        self.epub_options_group.setVisible(False)

        # Connect radio buttons to show/hide options
        self.txt_radio.toggled.connect(self._on_format_changed)
        self.epub_radio.toggled.connect(self._on_format_changed)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_format_changed(self):
        """Handle format selection change"""
        # Show EPUB options only when EPUB is selected
        self.epub_options_group.setVisible(self.epub_radio.isChecked())

    def get_format(self) -> str:
        """
        Get selected format.

        Returns:
            'txt' or 'epub'
        """
        return 'epub' if self.epub_radio.isChecked() else 'txt'

    def get_author(self) -> str:
        """
        Get author name for EPUB.

        Returns:
            Author name or 'Unknown'
        """
        author = self.author_input.text().strip()
        return author if author else "Unknown"
