import sys
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, 
    QHBoxLayout, QDialog, QLabel, QLineEdit, QCheckBox, QPushButton,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QAction, QFont, QUndoStack


# ============================================================================
# Configuration & Settings
# ============================================================================

class SettingsManager:
    """Manages application settings persistence and retrieval."""
    
    def __init__(self, config_path: str = ".editor_config.json"):
        self.config_path = Path(config_path)
        self.defaults = {
            "font_family": "Courier New",
            "font_size": 12,
            "tab_width": 4,
            "auto_indent": True,
            "encoding": "utf-8",
            "window_width": 1000,
            "window_height": 700,
            "recent_files": []
        }
        self.settings = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load settings from file or return defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return {**self.defaults, **json.load(f)}
            except Exception:
                return self.defaults.copy()
        return self.defaults.copy()
    
    def save(self):
        """Save current settings to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value


# ============================================================================
# File Management
# ============================================================================

class FileManager:
    """Manages all file I/O operations."""
    
    def __init__(self):
        self.current_file: Optional[Path] = None
        self.encoding = "utf-8"
    
    def detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    f.read()
                return enc
            except Exception:
                continue
        return 'utf-8'
    
    def read_file(self, file_path: Path) -> tuple[str, bool]:
        """Read file content. Returns (content, success)."""
        try:
            self.encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=self.encoding) as f:
                content = f.read()
            self.current_file = file_path
            return content, True
        except Exception as e:
            return f"Error reading file: {e}", False
    
    def write_file(self, file_path: Path, content: str) -> bool:
        """Write content to file."""
        try:
            with open(file_path, 'w', encoding=self.encoding) as f:
                f.write(content)
            self.current_file = file_path
            return True
        except Exception as e:
            print(f"Error writing file: {e}")
            return False
    
    def get_file_name(self) -> str:
        """Get current file name or 'Untitled'."""
        return self.current_file.name if self.current_file else "Untitled"


# ============================================================================
# Text Operations
# ============================================================================

class SelectionManager:
    """Handles text selection operations."""
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = text_edit
    
    def select_all(self):
        """Select all text."""
        self.text_edit.selectAll()
    
    def select_line(self):
        """Select current line."""
        cursor = self.text_edit.textCursor()
        cursor.select(cursor.LineUnderCursor)
        self.text_edit.setTextCursor(cursor)
    
    def select_word(self):
        """Select current word."""
        cursor = self.text_edit.textCursor()
        cursor.select(cursor.WordUnderCursor)
        self.text_edit.setTextCursor(cursor)


class ClipboardManager:
    """Manages clipboard operations."""
    
    def __init__(self, text_edit: QTextEdit):
        self.text_edit = text_edit
    
    def cut(self):
        self.text_edit.cut()
    
    def copy(self):
        self.text_edit.copy()
    
    def paste(self):
        self.text_edit.paste()


# ============================================================================
# Custom Text Editor Widget
# ============================================================================

class TextEditor(QTextEdit):
    """Custom QTextEdit widget with enhanced features."""
    
    def __init__(self, tab_width: int = 4, auto_indent: bool = True):
        super().__init__()
        self.tab_width = tab_width
        self.auto_indent = auto_indent
        
        # Setup font and properties
        font = QFont("Courier New", 12)
        font.setFixedPitch(True)
        self.setFont(font)
        
        self.setAcceptRichText(False)
        
        # Set tab width in pixels
        self.setTabStopDistance(self.tab_width * 8)
    
    def keyPressEvent(self, event):
        """Handle custom key press events."""
        if event.key() == Qt.Key.Key_Tab:
            # Insert spaces instead of tab
            self.insertPlainText(" " * self.tab_width)
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.auto_indent:
                self._handle_auto_indent()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    
    def _handle_auto_indent(self):
        """Handle auto-indentation on new line."""
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()
        
        # Count leading spaces
        indent = len(text) - len(text.lstrip())
        
        # Insert newline and matching indent
        cursor.insertText("\n" + " " * indent)
        self.setTextCursor(cursor)


# ============================================================================
# UI Managers
# ============================================================================

class MenuManager:
    """Creates and manages the menu bar."""
    
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.create_menus()
    
    def create_menus(self):
        """Create menu bar with File, Edit, View, Help menus."""
        menu_bar = self.main_window.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        self.new_action = file_menu.addAction("&New")
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        
        self.open_action = file_menu.addAction("&Open")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        
        self.save_action = file_menu.addAction("&Save")
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        
        self.save_as_action = file_menu.addAction("Save &As")
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        
        file_menu.addSeparator()
        self.exit_action = file_menu.addAction("E&xit")
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        self.undo_action = edit_menu.addAction("&Undo")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        
        self.redo_action = edit_menu.addAction("&Redo")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        
        edit_menu.addSeparator()
        self.cut_action = edit_menu.addAction("Cu&t")
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        
        self.copy_action = edit_menu.addAction("&Copy")
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        
        self.paste_action = edit_menu.addAction("&Paste")
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        
        edit_menu.addSeparator()
        self.select_all_action = edit_menu.addAction("Select &All")
        self.select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        
        self.select_line_action = edit_menu.addAction("Select &Line")
        self.select_word_action = edit_menu.addAction("Select &Word")
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        self.find_action = view_menu.addAction("&Find")
        self.find_action.setShortcut(QKeySequence.StandardKey.Find)
        
        self.find_replace_action = view_menu.addAction("Find & &Replace")
        self.find_replace_action.setShortcut(QKeySequence.StandardKey.Replace)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        self.about_action = help_menu.addAction("&About")


class ToolBarManager:
    """Manages toolbar with quick-access buttons."""
    
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.toolbar = self.main_window.addToolBar("Main Toolbar")
        self.create_toolbar()
    
    def create_toolbar(self):
        """Create toolbar buttons."""
        # Get actions from menu manager (assuming it's already created)
        menu_manager = self.main_window.menu_manager
        
        self.toolbar.addAction(menu_manager.new_action)
        self.toolbar.addAction(menu_manager.open_action)
        self.toolbar.addAction(menu_manager.save_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(menu_manager.cut_action)
        self.toolbar.addAction(menu_manager.copy_action)
        self.toolbar.addAction(menu_manager.paste_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(menu_manager.undo_action)
        self.toolbar.addAction(menu_manager.redo_action)


class StatusBarManager:
    """Updates status bar with line/column position, encoding, and modified status."""
    
    def __init__(self, main_window: QMainWindow, text_editor: TextEditor):
        self.main_window = main_window
        self.text_editor = text_editor
        self.status_bar = self.main_window.statusBar()
        
        # Position label
        self.position_label = QLabel("Line 1, Column 1")
        self.status_bar.addWidget(self.position_label)
        
        # Encoding label
        self.encoding_label = QLabel("UTF-8")
        self.status_bar.addPermanentWidget(self.encoding_label)
        
        # Connect signals
        self.text_editor.cursorPositionChanged.connect(self.update_position)
    
    def update_position(self):
        """Update line and column display."""
        cursor = self.text_editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock() + 1
        self.position_label.setText(f"Line {line}, Column {column}")
    
    def set_encoding(self, encoding: str):
        """Update encoding display."""
        self.encoding_label.setText(encoding.upper())


# ============================================================================
# Find & Replace
# ============================================================================

class FindReplaceDialog(QDialog):
    """Dialog for find/replace operations."""
    
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.text_editor = parent.text_editor
        self.search_engine = parent.search_engine
        self.setWindowTitle("Find & Replace")
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout()
        
        # Find section
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)
        
        # Replace section
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)
        
        # Options
        self.case_sensitive = QCheckBox("Case Sensitive")
        self.whole_word = QCheckBox("Whole Word")
        self.regex = QCheckBox("Regular Expression")
        
        layout.addWidget(self.case_sensitive)
        layout.addWidget(self.whole_word)
        layout.addWidget(self.regex)
        
        # Buttons
        button_layout = QHBoxLayout()
        find_button = QPushButton("Find All")
        find_button.clicked.connect(self.find_all)
        replace_button = QPushButton("Replace All")
        replace_button.clicked.connect(self.replace_all)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(find_button)
        button_layout.addWidget(replace_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setMinimumWidth(400)
    
    def find_all(self):
        """Find all occurrences."""
        pattern = self.find_input.text()
        if not pattern:
            return
        
        case_sensitive = self.case_sensitive.isChecked()
        whole_word = self.whole_word.isChecked()
        use_regex = self.regex.isChecked()
        
        results = self.search_engine.find_all(
            pattern, case_sensitive, whole_word, use_regex
        )
        
        QMessageBox.information(
            self, "Search Results",
            f"Found {len(results)} occurrence(s)."
        )
    
    def replace_all(self):
        """Replace all occurrences."""
        pattern = self.find_input.text()
        replacement = self.replace_input.text()
        
        if not pattern:
            return
        
        case_sensitive = self.case_sensitive.isChecked()
        whole_word = self.whole_word.isChecked()
        use_regex = self.regex.isChecked()
        
        count = self.search_engine.replace_all(
            pattern, replacement, case_sensitive, whole_word, use_regex
        )
        
        QMessageBox.information(
            self, "Replace Results",
            f"Replaced {count} occurrence(s)."
        )


class SearchEngine:
    """Backend logic for searching with regex, case sensitivity, and whole word options."""
    
    def __init__(self, text_editor: TextEditor):
        self.text_editor = text_editor
    
    def find_all(self, pattern: str, case_sensitive: bool = False,
                 whole_word: bool = False, use_regex: bool = False) -> list:
        """Find all occurrences of pattern."""
        text = self.text_editor.toPlainText()
        results = []
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            
            if use_regex:
                regex = re.compile(pattern, flags)
            else:
                pattern = re.escape(pattern)
                if whole_word:
                    pattern = r'\b' + pattern + r'\b'
                regex = re.compile(pattern, flags)
            
            for match in regex.finditer(text):
                results.append(match.span())
        except re.error:
            pass
        
        return results
    
    def replace_all(self, pattern: str, replacement: str,
                    case_sensitive: bool = False, whole_word: bool = False,
                    use_regex: bool = False) -> int:
        """Replace all occurrences and update text."""
        text = self.text_editor.toPlainText()
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            
            if use_regex:
                regex = re.compile(pattern, flags)
            else:
                pattern = re.escape(pattern)
                if whole_word:
                    pattern = r'\b' + pattern + r'\b'
                regex = re.compile(pattern, flags)
            
            new_text, count = regex.subn(replacement, text)
            self.text_editor.setPlainText(new_text)
            return count
        except re.error:
            return 0


# ============================================================================
# Main Application Window
# ============================================================================

class MainWindow(QMainWindow):
    """The main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize managers and components
        self.settings_manager = SettingsManager()
        self.file_manager = FileManager()
        
        # Create text editor
        self.text_editor = TextEditor(
            tab_width=self.settings_manager.get("tab_width", 4),
            auto_indent=self.settings_manager.get("auto_indent", True)
        )
        self.setCentralWidget(self.text_editor)
        
        # Initialize UI managers
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolBarManager(self)
        self.status_bar_manager = StatusBarManager(self, self.text_editor)
        
        # Initialize text operation managers
        self.selection_manager = SelectionManager(self.text_editor)
        self.clipboard_manager = ClipboardManager(self.text_editor)
        self.search_engine = SearchEngine(self.text_editor)
        
        # Setup undo/redo
        self.undo_stack = QUndoStack()
        self.text_editor.setUndoRedoEnabled(True)
        
        # Track file modification
        self.is_modified = False
        self.text_editor.textChanged.connect(self._on_text_changed)
        
        # Connect menu actions
        self._connect_actions()
        
        # Setup window
        self.setWindowTitle("Text Editor")
        self.resize(
            self.settings_manager.get("window_width", 1000),
            self.settings_manager.get("window_height", 700)
        )
    
    def _connect_actions(self):
        """Connect menu actions to functions."""
        # File menu
        self.menu_manager.new_action.triggered.connect(self.new_file)
        self.menu_manager.open_action.triggered.connect(self.open_file)
        self.menu_manager.save_action.triggered.connect(self.save_file)
        self.menu_manager.save_as_action.triggered.connect(self.save_as_file)
        self.menu_manager.exit_action.triggered.connect(self.close)
        
        # Edit menu
        self.menu_manager.undo_action.triggered.connect(self.text_editor.undo)
        self.menu_manager.redo_action.triggered.connect(self.text_editor.redo)
        self.menu_manager.cut_action.triggered.connect(self.clipboard_manager.cut)
        self.menu_manager.copy_action.triggered.connect(self.clipboard_manager.copy)
        self.menu_manager.paste_action.triggered.connect(self.clipboard_manager.paste)
        self.menu_manager.select_all_action.triggered.connect(self.selection_manager.select_all)
        self.menu_manager.select_line_action.triggered.connect(self.selection_manager.select_line)
        self.menu_manager.select_word_action.triggered.connect(self.selection_manager.select_word)
        
        # View menu
        self.menu_manager.find_action.triggered.connect(self.show_find_dialog)
        self.menu_manager.find_replace_action.triggered.connect(self.show_find_replace_dialog)
    
    def new_file(self):
        """Create a new file."""
        if self.is_modified and not self._confirm_discard():
            return
        
        self.text_editor.clear()
        self.file_manager.current_file = None
        self.is_modified = False
        self.setWindowTitle("Text Editor - Untitled")
    
    def open_file(self):
        """Open a file."""
        if self.is_modified and not self._confirm_discard():
            return
        
        file_path, _ = QFileDialog.getOpenFileName(self)
        if not file_path:
            return
        
        content, success = self.file_manager.read_file(Path(file_path))
        
        if success:
            self.text_editor.setPlainText(content)
            self.is_modified = False
            self._update_title()
            self.status_bar_manager.set_encoding(self.file_manager.encoding)
            
            # Add to recent files
            recent = self.settings_manager.get("recent_files", [])
            if file_path in recent:
                recent.remove(file_path)
            recent.insert(0, file_path)
            self.settings_manager.set("recent_files", recent[:10])
        else:
            QMessageBox.critical(self, "Error", content)
    
    def save_file(self):
        """Save current file."""
        if not self.file_manager.current_file:
            self.save_as_file()
            return
        
        content = self.text_editor.toPlainText()
        if self.file_manager.write_file(self.file_manager.current_file, content):
            self.is_modified = False
            self._update_title()
            QMessageBox.information(self, "Success", "File saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save file.")
    
    def save_as_file(self):
        """Save file with a new name."""
        file_path, _ = QFileDialog.getSaveFileName(self)
        if not file_path:
            return
        
        content = self.text_editor.toPlainText()
        if self.file_manager.write_file(Path(file_path), content):
            self.is_modified = False
            self._update_title()
            QMessageBox.information(self, "Success", "File saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save file.")
    
    def show_find_dialog(self):
        """Show find dialog."""
        dialog = FindReplaceDialog(self)
        dialog.replace_input.setVisible(False)
        dialog.exec()
    
    def show_find_replace_dialog(self):
        """Show find and replace dialog."""
        dialog = FindReplaceDialog(self)
        dialog.exec()
    
    def _on_text_changed(self):
        """Handle text change."""
        if not self.is_modified:
            self.is_modified = True
            self._update_title()
    
    def _update_title(self):
        """Update window title based on file state."""
        file_name = self.file_manager.get_file_name()
        modified = " *" if self.is_modified else ""
        self.setWindowTitle(f"Text Editor - {file_name}{modified}")
    
    def _confirm_discard(self) -> bool:
        """Ask user to confirm discarding changes."""
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Do you want to discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.is_modified and not self._confirm_discard():
            event.ignore()
            return
        
        # Save settings
        self.settings_manager.set("window_width", self.width())
        self.settings_manager.set("window_height", self.height())
        self.settings_manager.save()
        
        event.accept()


# ============================================================================
# Application Entry Point
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
