"""
URL History Panel - Shows search/fetch history and allows re-fetching.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QMenu
)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QAction
from datetime import datetime
from typing import List, Dict


class URLHistoryPanel(QWidget):
    """
    Panel showing URL search/fetch history.
    
    Features:
    - URL input field at top
    - List of past URLs with timestamps
    - Click to re-fetch
    - Right-click to copy/delete
    """
    
    # Signals
    fetch_url_clicked = Signal(str)  # URL to fetch
    
    MAX_HISTORY = 50  # Maximum history items to keep
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: List[Dict] = []
        self._history_visible = False  # Start collapsed
        self._init_ui()
        self._load_history()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # URL input section
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        title = QLabel("<b>🌐 Fetch Novel</b>")
        title.setStyleSheet("font-size: 14px;")
        input_layout.addWidget(title)
        
        # URL input row
        url_row = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter novel URL or search term...")
        self.url_input.returnPressed.connect(self._on_fetch)
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                font-size: 13px;
                border: 2px solid #d1d5db;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #6366f1;
            }
        """)
        url_row.addWidget(self.url_input)
        
        self.fetch_btn = QPushButton("🔍 Fetch")
        self.fetch_btn.clicked.connect(self._on_fetch)
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #4338ca;
            }
        """)
        url_row.addWidget(self.fetch_btn)
        
        input_layout.addLayout(url_row)
        layout.addWidget(input_frame)
        
        # History section header (clickable to toggle)
        history_header = QHBoxLayout()
        
        self.history_toggle_btn = QPushButton("▶ Recent Fetches")
        self.history_toggle_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                color: #6b7280;
                background: transparent;
                border: none;
                text-align: left;
                padding: 4px;
            }
            QPushButton:hover {
                color: #4b5563;
            }
        """)
        self.history_toggle_btn.clicked.connect(self._toggle_history)
        history_header.addWidget(self.history_toggle_btn)
        history_header.addStretch()
        
        layout.addLayout(history_header)
        
        # History container (collapsible)
        self.history_container = QWidget()
        history_container_layout = QVBoxLayout(self.history_container)
        history_container_layout.setContentsMargins(0, 0, 0, 0)
        history_container_layout.setSpacing(4)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(200)
        self.history_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #4b5563;
                border-radius: 6px;
                background: #374151;
                color: #f3f4f6;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #4b5563;
                color: #e5e7eb;
            }
            QListWidget::item:hover {
                background-color: #4b5563;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #6366f1;
                color: #ffffff;
            }
        """)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        self.history_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        history_container_layout.addWidget(self.history_list)
        
        # Clear history button
        clear_btn = QPushButton("🗑️ Clear History")
        clear_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                color: #6b7280;
                background: transparent;
                border: 1px solid #d1d5db;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                color: #dc2626;
                border-color: #fecaca;
            }
        """)
        clear_btn.clicked.connect(self._on_clear_history)
        history_container_layout.addWidget(clear_btn, alignment=Qt.AlignRight)
        
        layout.addWidget(self.history_container)
        
        # Start collapsed
        self.history_container.hide()
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def _toggle_history(self):
        """Toggle history section visibility"""
        self._history_visible = not self._history_visible
        if self._history_visible:
            self.history_container.show()
            self.history_toggle_btn.setText("▼ Recent Fetches")
        else:
            self.history_container.hide()
            self.history_toggle_btn.setText("▶ Recent Fetches")
    
    def _on_fetch(self):
        """Handle fetch button click"""
        url = self.url_input.text().strip()
        if url:
            self.add_to_history(url)
            self.fetch_url_clicked.emit(url)
            self.url_input.clear()
    
    def add_to_history(self, url: str, novel_title: str = ""):
        """Add a URL to history"""
        # Check if already exists
        for item in self._history:
            if item['url'] == url:
                # Move to top and update
                self._history.remove(item)
                break
        
        # Add new entry at top
        entry = {
            'url': url,
            'title': novel_title,
            'timestamp': datetime.now().isoformat(),
            'display_time': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self._history.insert(0, entry)
        
        # Limit history size
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[:self.MAX_HISTORY]
        
        self._save_history()
        self._refresh_list()
    
    def update_history_title(self, url: str, title: str):
        """Update the title for a URL in history (after successful fetch)"""
        for item in self._history:
            if item['url'] == url:
                item['title'] = title
                break
        self._save_history()
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the history list display"""
        self.history_list.clear()
        
        for entry in self._history:
            item = QListWidgetItem()
            
            # Format display
            title = entry.get('title') or entry['url']
            time_str = entry.get('display_time', '')
            
            # Truncate long URLs
            if len(title) > 60:
                title = title[:57] + "..."
            
            item.setText(f"{title}\n{time_str}")
            item.setData(Qt.UserRole, entry['url'])
            item.setToolTip(entry['url'])
            
            self.history_list.addItem(item)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on history item"""
        url = item.data(Qt.UserRole)
        if url:
            self.fetch_url_clicked.emit(url)
    
    def _show_context_menu(self, pos):
        """Show right-click context menu"""
        item = self.history_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        fetch_action = QAction("🔍 Fetch Again", self)
        fetch_action.triggered.connect(lambda: self._on_refetch(item))
        menu.addAction(fetch_action)
        
        copy_action = QAction("📋 Copy URL", self)
        copy_action.triggered.connect(lambda: self._on_copy_url(item))
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ Remove", self)
        delete_action.triggered.connect(lambda: self._on_delete_item(item))
        menu.addAction(delete_action)
        
        menu.exec(self.history_list.mapToGlobal(pos))
    
    def _on_refetch(self, item: QListWidgetItem):
        """Re-fetch a URL from history"""
        url = item.data(Qt.UserRole)
        if url:
            self.fetch_url_clicked.emit(url)
    
    def _on_copy_url(self, item: QListWidgetItem):
        """Copy URL to clipboard"""
        url = item.data(Qt.UserRole)
        if url:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(url)
    
    def _on_delete_item(self, item: QListWidgetItem):
        """Delete an item from history"""
        url = item.data(Qt.UserRole)
        self._history = [h for h in self._history if h['url'] != url]
        self._save_history()
        self._refresh_list()
    
    def _on_clear_history(self):
        """Clear all history"""
        self._history = []
        self._save_history()
        self._refresh_list()
    
    def _load_history(self):
        """Load history from settings"""
        settings = QSettings()
        history_json = settings.value("url_history", "[]")
        try:
            import json
            self._history = json.loads(history_json)
        except Exception:
            self._history = []
        self._refresh_list()
    
    def _save_history(self):
        """Save history to settings"""
        import json
        settings = QSettings()
        settings.setValue("url_history", json.dumps(self._history))
