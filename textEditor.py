import sys
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, 
    QHBoxLayout, QDialog, QLabel, QLineEdit, QCheckBox, QPushButton,
    QMenuBar, QStatusBar, QFileDialog, QMessageBox, QPlainTextEdit, QMenu,
    QTreeView, QDockWidget, QInputDialog, QHeaderView, QAbstractItemView,
    QTabWidget, QSplitter, QTabBar
)
from PyQt6.QtCore import QDir, QFileSystemWatcher, QModelIndex
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QKeySequence, QAction, QFont, QUndoStack, QColor, QPainter, QTextFormat, QTextCursor


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
            "recent_files": [],
            "dark_mode": False
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
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.text_edit.setTextCursor(cursor)
    
    def select_word(self):
        """Select current word."""
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
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
# Custom Text Editor Widget with Line Numbers
# ============================================================================

class AutoIndentManager:
    """Manages automatic indentation based on context."""
    
    INDENT_INCREASE_CHARS = ['{', '[', '(', ':']
    INDENT_DECREASE_CHARS = ['}', ']', ')']
    
    def __init__(self, editor, tab_width: int = 4):
        self.editor = editor
        self.tab_width = tab_width
    
    def get_line_indent(self, text: str) -> int:
        """Get the indentation level of a line (number of spaces)."""
        return len(text) - len(text.lstrip())
    
    def detect_indent_char(self, text: str) -> str:
        """Detect whether the document uses tabs or spaces."""
        for line in text.split('\n'):
            if line.startswith('\t'):
                return '\t'
            elif line.startswith(' '):
                return ' '
        return ' '
    
    def calculate_indent(self, cursor) -> str:
        """Calculate the appropriate indentation for a new line."""
        block = cursor.block()
        text = block.text()
        current_indent = self.get_line_indent(text)
        
        text_before_cursor = text[:cursor.positionInBlock()]
        stripped = text_before_cursor.rstrip()
        
        if stripped and stripped[-1] in self.INDENT_INCREASE_CHARS:
            current_indent += self.tab_width
        
        return ' ' * current_indent
    
    def should_decrease_indent(self, char: str, cursor) -> bool:
        """Check if we should decrease indent when typing a closing bracket."""
        if char not in self.INDENT_DECREASE_CHARS:
            return False
        
        block = cursor.block()
        text_before = block.text()[:cursor.positionInBlock()]
        return text_before.strip() == ''
    
    def get_decreased_indent(self, cursor) -> int:
        """Get the decreased indent level."""
        block = cursor.block()
        current_indent = self.get_line_indent(block.text())
        return max(0, current_indent - self.tab_width)


class BracketMatchManager:
    """Manages bracket matching and auto-closing."""
    
    BRACKETS = {
        '(': ')',
        '[': ']',
        '{': '}'
    }
    CLOSING_BRACKETS = {v: k for k, v in BRACKETS.items()}
    
    def __init__(self, editor):
        self.editor = editor
        self.matched_selections = []
    
    def get_matching_bracket(self, char: str) -> Optional[str]:
        """Get the closing bracket for an opening bracket."""
        return self.BRACKETS.get(char)
    
    def is_opening_bracket(self, char: str) -> bool:
        return char in self.BRACKETS
    
    def is_closing_bracket(self, char: str) -> bool:
        return char in self.CLOSING_BRACKETS
    
    def find_matching_bracket(self, cursor) -> Optional[int]:
        """Find the position of the matching bracket."""
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos >= len(text):
            return None
        
        char = text[pos] if pos < len(text) else ''
        
        if pos > 0 and text[pos - 1] in self.BRACKETS:
            char = text[pos - 1]
            pos = pos - 1
            search_forward = True
            target = self.BRACKETS[char]
        elif pos > 0 and text[pos - 1] in self.CLOSING_BRACKETS:
            char = text[pos - 1]
            pos = pos - 1
            search_forward = False
            target = self.CLOSING_BRACKETS[char]
        elif char in self.BRACKETS:
            search_forward = True
            target = self.BRACKETS[char]
        elif char in self.CLOSING_BRACKETS:
            search_forward = False
            target = self.CLOSING_BRACKETS[char]
        else:
            return None
        
        depth = 1
        if search_forward:
            for i in range(pos + 1, len(text)):
                if text[i] == char:
                    depth += 1
                elif text[i] == target:
                    depth -= 1
                    if depth == 0:
                        return i
        else:
            for i in range(pos - 1, -1, -1):
                if text[i] == char:
                    depth += 1
                elif text[i] == target:
                    depth -= 1
                    if depth == 0:
                        return i
        
        return None
    
    def highlight_matching_brackets(self, cursor, extra_selections: list, dark_mode: bool):
        """Add bracket highlighting to extra selections."""
        match_pos = self.find_matching_bracket(cursor)
        if match_pos is None:
            return
        
        if dark_mode:
            bracket_color = QColor("#4a4a00")
        else:
            bracket_color = QColor("#c0ffc0")
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        current_pos = None
        if pos > 0 and (text[pos - 1] in self.BRACKETS or text[pos - 1] in self.CLOSING_BRACKETS):
            current_pos = pos - 1
        elif pos < len(text) and (text[pos] in self.BRACKETS or text[pos] in self.CLOSING_BRACKETS):
            current_pos = pos
        
        if current_pos is not None:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(bracket_color)
            c = self.editor.textCursor()
            c.setPosition(current_pos)
            c.setPosition(current_pos + 1, c.MoveMode.KeepAnchor)
            selection.cursor = c
            extra_selections.append(selection)
        
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(bracket_color)
        c = self.editor.textCursor()
        c.setPosition(match_pos)
        c.setPosition(match_pos + 1, c.MoveMode.KeepAnchor)
        selection.cursor = c
        extra_selections.append(selection)
    
    def should_auto_close(self, char: str, cursor) -> bool:
        """Check if we should auto-insert the closing bracket."""
        if char not in self.BRACKETS:
            return False
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos < len(text):
            next_char = text[pos]
            if next_char.isalnum():
                return False
        
        return True
    
    def should_skip_closing(self, char: str, cursor) -> bool:
        """Check if we should skip over an existing closing bracket."""
        if char not in self.CLOSING_BRACKETS:
            return False
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos < len(text) and text[pos] == char:
            return True
        
        return False
    
    def should_delete_pair(self, cursor) -> bool:
        """Check if backspace should delete a bracket pair."""
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos > 0 and pos < len(text):
            prev_char = text[pos - 1]
            next_char = text[pos]
            if prev_char in self.BRACKETS and self.BRACKETS[prev_char] == next_char:
                return True
        
        return False


class QuoteMatchManager:
    """Manages quote matching and auto-closing."""
    
    QUOTES = ['"', "'", '`']
    
    def __init__(self, editor):
        self.editor = editor
    
    def is_quote(self, char: str) -> bool:
        return char in self.QUOTES
    
    def is_inside_quotes(self, cursor, quote_char: str) -> bool:
        """Check if cursor is inside a quoted string."""
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        line_start = text.rfind('\n', 0, pos)
        line_start = 0 if line_start == -1 else line_start + 1
        
        line_text = text[line_start:pos]
        count = line_text.count(quote_char)
        
        return count % 2 == 1
    
    def should_auto_close(self, char: str, cursor) -> bool:
        """Check if we should auto-insert the closing quote."""
        if char not in self.QUOTES:
            return False
        
        if self.is_inside_quotes(cursor, char):
            return False
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos < len(text):
            next_char = text[pos]
            if next_char.isalnum():
                return False
        
        if pos > 0:
            prev_char = text[pos - 1]
            if prev_char.isalnum() or prev_char == '\\':
                return False
        
        return True
    
    def should_skip_closing(self, char: str, cursor) -> bool:
        """Check if we should skip over an existing closing quote."""
        if char not in self.QUOTES:
            return False
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos < len(text) and text[pos] == char:
            if self.is_inside_quotes(cursor, char):
                return True
        
        return False
    
    def should_delete_pair(self, cursor) -> bool:
        """Check if backspace should delete a quote pair."""
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos > 0 and pos < len(text):
            prev_char = text[pos - 1]
            next_char = text[pos]
            if prev_char in self.QUOTES and prev_char == next_char:
                return True
        
        return False
    
    def wrap_selection(self, cursor, quote_char: str) -> bool:
        """Wrap selected text with quotes."""
        if not cursor.hasSelection():
            return False
        
        selected = cursor.selectedText()
        cursor.insertText(f"{quote_char}{selected}{quote_char}")
        return True
    
    def find_matching_quote(self, cursor) -> Optional[int]:
        """Find the position of the matching quote."""
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        if pos >= len(text) and pos == 0:
            return None
        
        # Check character before cursor or at cursor
        quote_char = None
        check_pos = None
        
        if pos > 0 and text[pos - 1] in self.QUOTES:
            quote_char = text[pos - 1]
            check_pos = pos - 1
        elif pos < len(text) and text[pos] in self.QUOTES:
            quote_char = text[pos]
            check_pos = pos
        
        if quote_char is None:
            return None
        
        # Find line boundaries
        line_start = text.rfind('\n', 0, check_pos)
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find('\n', check_pos)
        line_end = len(text) if line_end == -1 else line_end
        
        line_text = text[line_start:line_end]
        pos_in_line = check_pos - line_start
        
        # Count quotes before this position to determine if opening or closing
        quotes_before = line_text[:pos_in_line].count(quote_char)
        
        if quotes_before % 2 == 0:
            # This is an opening quote, find closing
            for i in range(check_pos + 1, line_end):
                if text[i] == quote_char and (i == 0 or text[i - 1] != '\\'):
                    return i
        else:
            # This is a closing quote, find opening
            for i in range(check_pos - 1, line_start - 1, -1):
                if text[i] == quote_char and (i == 0 or text[i - 1] != '\\'):
                    return i
        
        return None
    
    def highlight_matching_quotes(self, cursor, extra_selections: list, dark_mode: bool):
        """Add quote highlighting to extra selections."""
        match_pos = self.find_matching_quote(cursor)
        if match_pos is None:
            return
        
        if dark_mode:
            quote_color = QColor("#4a004a")  # Purple tint for dark mode
        else:
            quote_color = QColor("#ffc0ff")  # Light purple for light mode
        
        text = self.editor.toPlainText()
        pos = cursor.position()
        
        # Find current quote position
        current_pos = None
        if pos > 0 and text[pos - 1] in self.QUOTES:
            current_pos = pos - 1
        elif pos < len(text) and text[pos] in self.QUOTES:
            current_pos = pos
        
        if current_pos is not None:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(quote_color)
            c = self.editor.textCursor()
            c.setPosition(current_pos)
            c.setPosition(current_pos + 1, c.MoveMode.KeepAnchor)
            selection.cursor = c
            extra_selections.append(selection)
        
        # Highlight matching quote
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(quote_color)
        c = self.editor.textCursor()
        c.setPosition(match_pos)
        c.setPosition(match_pos + 1, c.MoveMode.KeepAnchor)
        selection.cursor = c
        extra_selections.append(selection)


class MultiCursorManager:
    """Manages multiple cursors for simultaneous editing."""
    
    def __init__(self, editor):
        self.editor = editor
        self.cursors: list[QTextCursor] = []
        self.active = False
    
    def add_cursor(self, cursor: QTextCursor):
        """Add a new cursor at the specified position."""
        # Avoid duplicate cursors at same position
        for existing in self.cursors:
            if existing.position() == cursor.position():
                return
        
        new_cursor = QTextCursor(cursor)
        self.cursors.append(new_cursor)
        self.active = True
    
    def clear(self):
        """Clear all extra cursors."""
        self.cursors.clear()
        self.active = False
    
    def has_cursors(self) -> bool:
        """Check if there are multiple cursors."""
        return self.active and len(self.cursors) > 0
    
    def get_all_cursors(self) -> list[QTextCursor]:
        """Get all cursors including the main one."""
        main_cursor = self.editor.textCursor()
        if not self.active:
            return [main_cursor]
        return [main_cursor] + self.cursors
    
    def insert_text(self, text: str):
        """Insert text at all cursor positions."""
        if not self.active:
            return False
        
        # Sort cursors by position (descending) to avoid position shifts
        all_cursors = self.get_all_cursors()
        all_cursors.sort(key=lambda c: c.position(), reverse=True)
        
        # Begin edit block for undo grouping
        main_cursor = self.editor.textCursor()
        main_cursor.beginEditBlock()
        
        for cursor in all_cursors:
            cursor.insertText(text)
        
        main_cursor.endEditBlock()
        self._update_cursor_positions_after_edit()
        return True
    
    def delete_char(self, backwards: bool = True):
        """Delete character at all cursor positions."""
        if not self.active:
            return False
        
        all_cursors = self.get_all_cursors()
        all_cursors.sort(key=lambda c: c.position(), reverse=True)
        
        main_cursor = self.editor.textCursor()
        main_cursor.beginEditBlock()
        
        for cursor in all_cursors:
            if backwards:
                cursor.deletePreviousChar()
            else:
                cursor.deleteChar()
        
        main_cursor.endEditBlock()
        self._update_cursor_positions_after_edit()
        return True
    
    def move_cursors(self, operation, mode=QTextCursor.MoveMode.MoveAnchor):
        """Move all cursors with the given operation."""
        if not self.active:
            return False
        
        for cursor in self.cursors:
            cursor.movePosition(operation, mode)
        return True
    
    def _update_cursor_positions_after_edit(self):
        """Update cursor list after edits - remove invalid/duplicate cursors."""
        seen_positions = {self.editor.textCursor().position()}
        valid_cursors = []
        
        for cursor in self.cursors:
            pos = cursor.position()
            if pos not in seen_positions:
                seen_positions.add(pos)
                valid_cursors.append(cursor)
        
        self.cursors = valid_cursors
        if not self.cursors:
            self.active = False
    
    def add_cursor_above(self):
        """Add a cursor on the line above each current cursor."""
        all_cursors = self.get_all_cursors()
        new_cursors = []
        
        for cursor in all_cursors:
            new_cursor = QTextCursor(cursor)
            if new_cursor.movePosition(QTextCursor.MoveOperation.Up):
                new_cursors.append(new_cursor)
        
        for c in new_cursors:
            self.add_cursor(c)
    
    def add_cursor_below(self):
        """Add a cursor on the line below each current cursor."""
        all_cursors = self.get_all_cursors()
        new_cursors = []
        
        for cursor in all_cursors:
            new_cursor = QTextCursor(cursor)
            if new_cursor.movePosition(QTextCursor.MoveOperation.Down):
                new_cursors.append(new_cursor)
        
        for c in new_cursors:
            self.add_cursor(c)
    
    def highlight_cursors(self, extra_selections: list, dark_mode: bool):
        """Add visual highlights for extra cursors."""
        if not self.active:
            return
        
        cursor_color = QColor("#ff6b6b") if dark_mode else QColor("#ff4444")
        
        for cursor in self.cursors:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(cursor_color)
            c = QTextCursor(cursor)
            # Highlight a thin line at cursor position
            if c.position() < len(self.editor.toPlainText()):
                c.setPosition(c.position())
                c.setPosition(c.position() + 1, QTextCursor.MoveMode.KeepAnchor)
            selection.cursor = c
            extra_selections.append(selection)


class RectangularSelectionManager:
    """Manages rectangular/column selection."""
    
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.start_pos = None  # (line, column)
        self.end_pos = None    # (line, column)
    
    def start_selection(self, line: int, column: int):
        """Start a rectangular selection."""
        self.active = True
        self.start_pos = (line, column)
        self.end_pos = (line, column)
    
    def update_selection(self, line: int, column: int):
        """Update the end position of rectangular selection."""
        if self.active:
            self.end_pos = (line, column)
    
    def clear(self):
        """Clear the rectangular selection."""
        self.active = False
        self.start_pos = None
        self.end_pos = None
    
    def get_selection_range(self) -> tuple:
        """Get the normalized selection range."""
        if not self.active or not self.start_pos or not self.end_pos:
            return None
        
        start_line = min(self.start_pos[0], self.end_pos[0])
        end_line = max(self.start_pos[0], self.end_pos[0])
        start_col = min(self.start_pos[1], self.end_pos[1])
        end_col = max(self.start_pos[1], self.end_pos[1])
        
        return (start_line, end_line, start_col, end_col)
    
    def get_selected_text(self) -> list[str]:
        """Get the text from each line in the rectangular selection."""
        range_info = self.get_selection_range()
        if not range_info:
            return []
        
        start_line, end_line, start_col, end_col = range_info
        text = self.editor.toPlainText()
        lines = text.split('\n')
        
        selected = []
        for i in range(start_line, end_line + 1):
            if i < len(lines):
                line = lines[i]
                # Pad line if it's shorter than start_col
                if len(line) < start_col:
                    selected.append('')
                else:
                    selected.append(line[start_col:end_col])
        
        return selected
    
    def highlight_selection(self, extra_selections: list, dark_mode: bool):
        """Add visual highlights for rectangular selection."""
        if not self.active:
            return
        
        range_info = self.get_selection_range()
        if not range_info:
            return
        
        start_line, end_line, start_col, end_col = range_info
        rect_color = QColor("#264f78") if dark_mode else QColor("#add6ff")
        
        doc = self.editor.document()
        
        for line_num in range(start_line, end_line + 1):
            block = doc.findBlockByLineNumber(line_num)
            if not block.isValid():
                continue
            
            line_text = block.text()
            actual_start = min(start_col, len(line_text))
            actual_end = min(end_col, len(line_text))
            
            if actual_start < actual_end:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(rect_color)
                
                cursor = QTextCursor(block)
                cursor.setPosition(block.position() + actual_start)
                cursor.setPosition(block.position() + actual_end, QTextCursor.MoveMode.KeepAnchor)
                selection.cursor = cursor
                extra_selections.append(selection)
    
    def create_cursors_from_selection(self, multi_cursor_mgr: 'MultiCursorManager'):
        """Convert rectangular selection to multiple cursors."""
        range_info = self.get_selection_range()
        if not range_info:
            return
        
        start_line, end_line, start_col, end_col = range_info
        doc = self.editor.document()
        
        # Use the end column for cursor placement
        col = end_col
        
        for line_num in range(start_line, end_line + 1):
            block = doc.findBlockByLineNumber(line_num)
            if not block.isValid():
                continue
            
            cursor = QTextCursor(block)
            line_length = len(block.text())
            target_col = min(col, line_length)
            cursor.setPosition(block.position() + target_col)
            
            if line_num == start_line:
                # Set as main cursor
                self.editor.setTextCursor(cursor)
            else:
                multi_cursor_mgr.add_cursor(cursor)
        
        self.clear()


class LineNumberArea(QWidget):
    """Widget for displaying line numbers."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class TextEditor(QPlainTextEdit):
    """Custom QPlainTextEdit widget with line numbers and enhanced features."""
    
    def __init__(self, tab_width: int = 4, auto_indent: bool = True):
        super().__init__()
        self.tab_width = tab_width
        self.auto_indent = auto_indent
        self.dark_mode = False
        
        # Setup font and properties
        font = QFont("Courier New", 12)
        font.setFixedPitch(True)
        self.setFont(font)
        
        # Set tab width in pixels
        self.setTabStopDistance(self.tab_width * 8)
        
        # Create line number area
        self.line_number_area = LineNumberArea(self)
        
        # Initialize managers
        self.indent_manager = AutoIndentManager(self, tab_width)
        self.bracket_manager = BracketMatchManager(self)
        self.quote_manager = QuoteMatchManager(self)
        self.multi_cursor_manager = MultiCursorManager(self)
        self.rect_selection_manager = RectangularSelectionManager(self)
        
        # Connect signals for line number updates
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.apply_theme()
    
    def line_number_area_width(self):
        """Calculate the width needed for line numbers."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, _):
        """Update the viewport margins to accommodate line numbers."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """Scroll or update the line number area."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """Handle resize to adjust line number area."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
    
    def line_number_area_paint_event(self, event):
        """Paint the line numbers."""
        painter = QPainter(self.line_number_area)
        
        if self.dark_mode:
            painter.fillRect(event.rect(), QColor("#2d2d2d"))
            number_color = QColor("#888888")
            current_line_color = QColor("#ffffff")
        else:
            painter.fillRect(event.rect(), QColor("#f0f0f0"))
            number_color = QColor("#888888")
            current_line_color = QColor("#000000")
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        current_block_number = self.textCursor().blockNumber()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_block_number:
                    painter.setPen(current_line_color)
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                else:
                    painter.setPen(number_color)
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)
                painter.drawText(0, top, self.line_number_area.width() - 5, 
                               self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
    
    def highlight_current_line(self):
        """Highlight the current line and matching brackets."""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            if self.dark_mode:
                line_color = QColor("#3d3d3d")
            else:
                line_color = QColor("#e6f3ff")
            
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        # Add bracket matching highlights
        self.bracket_manager.highlight_matching_brackets(
            self.textCursor(), extra_selections, self.dark_mode
        )
        
        # Add quote matching highlights
        self.quote_manager.highlight_matching_quotes(
            self.textCursor(), extra_selections, self.dark_mode
        )
        
        # Add multi-cursor highlights
        self.multi_cursor_manager.highlight_cursors(extra_selections, self.dark_mode)
        
        # Add rectangular selection highlights
        self.rect_selection_manager.highlight_selection(extra_selections, self.dark_mode)
        
        self.setExtraSelections(extra_selections)
    
    def set_dark_mode(self, enabled: bool):
        """Set dark or light mode."""
        self.dark_mode = enabled
        self.apply_theme()
        self.highlight_current_line()
        self.line_number_area.update()
    
    def apply_theme(self):
        """Apply the current theme colors."""
        if self.dark_mode:
            self.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
            """)
        else:
            self.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                }
            """)
    
    def keyPressEvent(self, event):
        """Handle custom key press events."""
        cursor = self.textCursor()
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # Handle Escape - clear multi-cursor and rectangular selection
        if key == Qt.Key.Key_Escape:
            if self.multi_cursor_manager.has_cursors() or self.rect_selection_manager.active:
                self.multi_cursor_manager.clear()
                self.rect_selection_manager.clear()
                self.highlight_current_line()
                return
        
        # Handle Ctrl+Alt+Up - add cursor above
        if key == Qt.Key.Key_Up and modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            self.multi_cursor_manager.add_cursor_above()
            self.highlight_current_line()
            return
        
        # Handle Ctrl+Alt+Down - add cursor below
        if key == Qt.Key.Key_Down and modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            self.multi_cursor_manager.add_cursor_below()
            self.highlight_current_line()
            return
        
        # Convert rectangular selection to cursors when user starts typing
        if self.rect_selection_manager.active:
            if text and len(text) == 1:
                self.rect_selection_manager.create_cursors_from_selection(self.multi_cursor_manager)
                self.highlight_current_line()
                # Fall through to handle the typed character with multi-cursors
        
        # Handle multi-cursor text input
        if self.multi_cursor_manager.has_cursors():
            if key == Qt.Key.Key_Backspace:
                # Delete at extra cursors only, let main cursor be handled normally
                self._multi_cursor_delete(backwards=True)
                super().keyPressEvent(event)
                self.highlight_current_line()
                return
            
            if key == Qt.Key.Key_Delete:
                self._multi_cursor_delete(backwards=False)
                super().keyPressEvent(event)
                self.highlight_current_line()
                return
            
            if text and len(text) == 1:
                # Insert at extra cursors only, main cursor handled by super()
                self._multi_cursor_insert(text)
                super().keyPressEvent(event)
                self.highlight_current_line()
                return
        
        # Handle Tab
        if key == Qt.Key.Key_Tab:
            if self.multi_cursor_manager.has_cursors():
                self.multi_cursor_manager.insert_text(" " * self.tab_width)
                self.highlight_current_line()
            else:
                self.insertPlainText(" " * self.tab_width)
            return
        
        # Handle Enter/Return with auto-indent
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            if self.multi_cursor_manager.has_cursors():
                self.multi_cursor_manager.insert_text("\n")
                self.highlight_current_line()
            elif self.auto_indent:
                self._handle_auto_indent()
            else:
                super().keyPressEvent(event)
            return
        
        # Handle Backspace - delete pairs and smart indent
        if key == Qt.Key.Key_Backspace:
            if self.bracket_manager.should_delete_pair(cursor):
                cursor.deleteChar()  # Delete the closing bracket
                super().keyPressEvent(event)  # Delete the opening bracket
                return
            if self.quote_manager.should_delete_pair(cursor):
                cursor.deleteChar()  # Delete the closing quote
                super().keyPressEvent(event)  # Delete the opening quote
                return
            
            # Smart backspace: delete tab_width spaces at a time on indented lines
            block = cursor.block()
            text_before = block.text()[:cursor.positionInBlock()]
            
            if text_before and text_before.strip() == '':
                # We're in leading whitespace
                indent = len(text_before)
                if indent > 0:
                    # Calculate how many spaces to delete (back to previous tab stop)
                    spaces_to_delete = indent % self.tab_width
                    if spaces_to_delete == 0:
                        spaces_to_delete = self.tab_width
                    spaces_to_delete = min(spaces_to_delete, indent)
                    
                    for _ in range(spaces_to_delete):
                        cursor.deletePreviousChar()
                    return
            
            super().keyPressEvent(event)
            return
        
        # Handle character input
        if text and len(text) == 1:
            char = text
            
            # Handle quotes with selection wrapping
            if self.quote_manager.is_quote(char) and cursor.hasSelection():
                self.quote_manager.wrap_selection(cursor, char)
                return
            
            # Skip over closing brackets
            if self.bracket_manager.should_skip_closing(char, cursor):
                cursor.movePosition(cursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return
            
            # Skip over closing quotes
            if self.quote_manager.should_skip_closing(char, cursor):
                cursor.movePosition(cursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return
            
            # Auto-close brackets
            if self.bracket_manager.should_auto_close(char, cursor):
                closing = self.bracket_manager.get_matching_bracket(char)
                cursor.insertText(char + closing)
                cursor.movePosition(cursor.MoveOperation.Left)
                self.setTextCursor(cursor)
                return
            
            # Auto-close quotes
            if self.quote_manager.should_auto_close(char, cursor):
                cursor.insertText(char + char)
                cursor.movePosition(cursor.MoveOperation.Left)
                self.setTextCursor(cursor)
                return
            
            # Handle auto-dedent for closing brackets (without auto-close)
            if self.indent_manager.should_decrease_indent(char, cursor):
                new_indent = self.indent_manager.get_decreased_indent(cursor)
                cursor.select(cursor.SelectionType.LineUnderCursor)
                line_text = cursor.selectedText()
                cursor.insertText(' ' * new_indent + char)
                return
        
        super().keyPressEvent(event)
    
    def _handle_auto_indent(self):
        """Handle auto-indentation on new line."""
        cursor = self.textCursor()
        text = self.toPlainText()
        pos = cursor.position()
        
        # Check if we're between matching brackets
        if pos > 0 and pos < len(text):
            char_before = text[pos - 1]
            char_after = text[pos]
            
            if char_before in self.bracket_manager.BRACKETS:
                expected_closing = self.bracket_manager.BRACKETS[char_before]
                if char_after == expected_closing:
                    # We're between brackets like {|} or (|)
                    # Get the indent of the line with the opening bracket
                    block = cursor.block()
                    line_text = block.text()
                    base_indent = len(line_text) - len(line_text.lstrip())
                    
                    # Round down to nearest tab stop for closing bracket
                    closing_indent = (base_indent // self.tab_width) * self.tab_width
                    
                    # Content gets one more level of indentation
                    content_indent = closing_indent + self.tab_width
                    
                    # Insert: newline + content indent + newline + closing indent
                    cursor.insertText("\n" + " " * content_indent + "\n" + " " * closing_indent)
                    # Move cursor back to the content line
                    cursor.movePosition(cursor.MoveOperation.Up)
                    cursor.movePosition(cursor.MoveOperation.EndOfLine)
                    self.setTextCursor(cursor)
                    return
        
        # Normal auto-indent
        indent = self.indent_manager.calculate_indent(cursor)
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)
    
    def mousePressEvent(self, event):
        """Handle mouse press for multi-cursor and rectangular selection."""
        modifiers = event.modifiers()
        
        # Alt+Shift+Click: Start rectangular selection (check first, before Alt+Click)
        if event.button() == Qt.MouseButton.LeftButton and (modifiers & Qt.KeyboardModifier.AltModifier) and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            # Clear any existing multi-cursors when starting rect selection
            self.multi_cursor_manager.clear()
            cursor = self.cursorForPosition(event.pos())
            block = cursor.block()
            line = block.blockNumber()
            column = cursor.positionInBlock()
            self.rect_selection_manager.start_selection(line, column)
            self.highlight_current_line()
            return
        
        # Alt+Click: Add cursor at click position (only if not doing rect selection)
        if event.button() == Qt.MouseButton.LeftButton and modifiers == Qt.KeyboardModifier.AltModifier:
            cursor = self.cursorForPosition(event.pos())
            self.multi_cursor_manager.add_cursor(cursor)
            self.highlight_current_line()
            return
        
        # Clear multi-cursor on regular click (without modifiers)
        if event.button() == Qt.MouseButton.LeftButton and modifiers == Qt.KeyboardModifier.NoModifier:
            if self.multi_cursor_manager.has_cursors():
                self.multi_cursor_manager.clear()
                self.highlight_current_line()
            if self.rect_selection_manager.active:
                self.rect_selection_manager.clear()
                self.highlight_current_line()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for rectangular selection."""
        if self.rect_selection_manager.active:
            cursor = self.cursorForPosition(event.pos())
            block = cursor.block()
            line = block.blockNumber()
            column = cursor.positionInBlock()
            self.rect_selection_manager.update_selection(line, column)
            self.highlight_current_line()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to finalize rectangular selection."""
        # Keep rectangular selection active - don't convert to cursors yet
        # Conversion happens when user starts typing
        super().mouseReleaseEvent(event)
    
    def _get_cursor_line_column(self, cursor) -> tuple[int, int]:
        """Get line and column for a cursor."""
        block = cursor.block()
        return (block.blockNumber(), cursor.positionInBlock())
    
    def _multi_cursor_insert(self, text: str):
        """Insert text at extra cursors only (main cursor handled separately)."""
        if not self.multi_cursor_manager.cursors:
            return
        
        # Sort by position descending to avoid position shifts
        cursors = sorted(self.multi_cursor_manager.cursors, key=lambda c: c.position(), reverse=True)
        
        for cursor in cursors:
            cursor.insertText(text)
        
        self.multi_cursor_manager._update_cursor_positions_after_edit()
    
    def _multi_cursor_delete(self, backwards: bool = True):
        """Delete at extra cursors only (main cursor handled separately)."""
        if not self.multi_cursor_manager.cursors:
            return
        
        # Sort by position descending to avoid position shifts
        cursors = sorted(self.multi_cursor_manager.cursors, key=lambda c: c.position(), reverse=True)
        
        for cursor in cursors:
            if backwards:
                cursor.deletePreviousChar()
            else:
                cursor.deleteChar()
        
        self.multi_cursor_manager._update_cursor_positions_after_edit()


# ============================================================================
# Multi-File Tab Support
# ============================================================================

class EditorTab:
    """Represents a single file tab with its editor and metadata."""
    
    def __init__(self, editor: TextEditor, file_path: Optional[Path] = None):
        self.editor = editor
        self.file_path = file_path
        self.is_modified = False
        self.encoding = "utf-8"
    
    @property
    def name(self) -> str:
        if self.file_path:
            return self.file_path.name
        return "Untitled"
    
    @property
    def display_name(self) -> str:
        return f"{self.name} *" if self.is_modified else self.name


class EditorTabWidget(QTabWidget):
    """Tab widget for managing multiple editor tabs."""
    
    tab_changed = pyqtSignal(object)  # Emits EditorTab
    all_tabs_closed = pyqtSignal()
    tab_dropped = pyqtSignal(object, object)  # source_tab_widget, tab
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.tabs: list[EditorTab] = []
        self.dark_mode = False
        
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setAcceptDrops(True)
        
        # Enable drag from tab bar
        self.tabBar().setAcceptDrops(True)
        self.tabBar().setChangeCurrentOnDrag(True)
        
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._on_tab_changed)
        
        self.new_tab()
    
    def new_tab(self, file_path: Optional[Path] = None, content: str = "") -> EditorTab:
        """Create a new editor tab."""
        editor = TextEditor(
            tab_width=self.settings_manager.get("tab_width", 4),
            auto_indent=self.settings_manager.get("auto_indent", True)
        )
        editor.set_dark_mode(self.dark_mode)
        
        if content:
            editor.setPlainText(content)
        
        tab = EditorTab(editor, file_path)
        self.tabs.append(tab)
        
        index = self.addTab(editor, tab.name)
        self.setCurrentIndex(index)
        
        editor.textChanged.connect(lambda: self._on_text_changed(tab))
        
        return tab
    
    def _on_text_changed(self, tab: EditorTab):
        """Handle text changes in a tab."""
        if not tab.is_modified:
            tab.is_modified = True
            self._update_tab_title(tab)
    
    def _update_tab_title(self, tab: EditorTab):
        """Update the tab title to reflect modified state."""
        index = self.tabs.index(tab)
        self.setTabText(index, tab.display_name)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        if 0 <= index < len(self.tabs):
            self.tab_changed.emit(self.tabs[index])
    
    def _close_tab(self, index: int):
        """Close a tab, prompting to save if modified."""
        if index < 0 or index >= len(self.tabs):
            return
        
        tab = self.tabs[index]
        
        if tab.is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"'{tab.name}' has unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Save:
                if not self._save_tab(tab):
                    return
        
        self.removeTab(index)
        self.tabs.pop(index)
        
        if len(self.tabs) == 0:
            self.all_tabs_closed.emit()
    
    def _save_tab(self, tab: EditorTab) -> bool:
        """Save a tab's content. Returns True if saved successfully."""
        if not tab.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self)
            if not file_path:
                return False
            tab.file_path = Path(file_path)
        
        try:
            with open(tab.file_path, 'w', encoding=tab.encoding) as f:
                f.write(tab.editor.toPlainText())
            tab.is_modified = False
            self._update_tab_title(tab)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
            return False
    
    def current_tab(self) -> Optional[EditorTab]:
        """Get the currently active tab."""
        index = self.currentIndex()
        if 0 <= index < len(self.tabs):
            return self.tabs[index]
        return None
    
    def open_file(self, file_path: Path, content: str, encoding: str = "utf-8") -> EditorTab:
        """Open a file in a new tab or switch to existing tab."""
        for i, tab in enumerate(self.tabs):
            if tab.file_path == file_path:
                self.setCurrentIndex(i)
                return tab
        
        tab = self.new_tab(file_path, content)
        tab.encoding = encoding
        tab.is_modified = False
        self._update_tab_title(tab)
        return tab
    
    def save_current(self) -> bool:
        """Save the current tab."""
        tab = self.current_tab()
        if tab:
            return self._save_tab(tab)
        return False
    
    def save_current_as(self) -> bool:
        """Save the current tab with a new name."""
        tab = self.current_tab()
        if not tab:
            return False
        
        file_path, _ = QFileDialog.getSaveFileName(self)
        if not file_path:
            return False
        
        tab.file_path = Path(file_path)
        return self._save_tab(tab)
    
    def receive_tab(self, tab: EditorTab):
        """Receive a tab from another tab widget."""
        tab.editor.set_dark_mode(self.dark_mode)
        self.tabs.append(tab)
        index = self.addTab(tab.editor, tab.display_name)
        self.setCurrentIndex(index)
        tab.editor.textChanged.connect(lambda: self._on_text_changed(tab))
    
    def remove_tab_without_close(self, index: int) -> Optional[EditorTab]:
        """Remove a tab without closing it (for transfer)."""
        if index < 0 or index >= len(self.tabs):
            return None
        
        tab = self.tabs.pop(index)
        self.removeTab(index)
        
        if len(self.tabs) == 0:
            self.all_tabs_closed.emit()
        
        return tab
    
    def set_dark_mode(self, enabled: bool):
        """Apply dark mode to all editors."""
        self.dark_mode = enabled
        for tab in self.tabs:
            tab.editor.set_dark_mode(enabled)
        
        if enabled:
            self.setStyleSheet("""
                QTabWidget::pane { border: none; background-color: #1e1e1e; }
                QTabBar::tab { 
                    background-color: #2d2d2d; 
                    color: #d4d4d4; 
                    padding: 6px 12px;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                }
                QTabBar::tab:selected { background-color: #1e1e1e; }
                QTabBar::tab:hover { background-color: #3d3d3d; }
            """)
        else:
            self.setStyleSheet("""
                QTabWidget::pane { border: none; }
                QTabBar::tab { 
                    background-color: #e0e0e0; 
                    padding: 6px 12px;
                    border: none;
                    border-right: 1px solid #cccccc;
                }
                QTabBar::tab:selected { background-color: #ffffff; }
                QTabBar::tab:hover { background-color: #f0f0f0; }
            """)


class SplitPaneWidget(QWidget):
    """Wrapper widget for EditorTabWidget with a close button."""
    
    close_requested = pyqtSignal(object)
    
    def __init__(self, tab_widget: EditorTabWidget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.dark_mode = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with close button
        self.header = QWidget()
        self.header.setFixedHeight(20)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 2, 0)
        header_layout.setSpacing(0)
        header_layout.addStretch()
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setFlat(True)
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        self.close_btn.setToolTip("Close split")
        header_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.header)
        layout.addWidget(tab_widget)
        
        self.apply_theme(False)
    
    def apply_theme(self, dark_mode: bool):
        self.dark_mode = dark_mode
        if dark_mode:
            self.header.setStyleSheet("background-color: #2d2d2d;")
            self.close_btn.setStyleSheet("""
                QPushButton { color: #888888; background: transparent; border: none; font-size: 14px; }
                QPushButton:hover { color: #ffffff; background-color: #c42b1c; }
            """)
        else:
            self.header.setStyleSheet("background-color: #e0e0e0;")
            self.close_btn.setStyleSheet("""
                QPushButton { color: #666666; background: transparent; border: none; font-size: 14px; }
                QPushButton:hover { color: #ffffff; background-color: #c42b1c; }
            """)


class EditorPane(QWidget):
    """A pane that can contain tabs and be split."""
    
    file_opened = pyqtSignal(str)
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.dark_mode = False
        self.active_tab_widget: Optional[EditorTabWidget] = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        self.tab_widgets: list[EditorTabWidget] = []
        self.split_panes: list[SplitPaneWidget] = []
        self._add_tab_widget()
    
    def _add_tab_widget(self) -> EditorTabWidget:
        """Add a new tab widget to the splitter."""
        tab_widget = EditorTabWidget(self.settings_manager)
        tab_widget.set_dark_mode(self.dark_mode)
        tab_widget.all_tabs_closed.connect(lambda: self._remove_tab_widget(tab_widget))
        tab_widget.currentChanged.connect(lambda: self._set_active_tab_widget(tab_widget))
        
        # Track when user clicks in this tab widget
        tab_widget.tabBar().installEventFilter(self)
        
        self.tab_widgets.append(tab_widget)
        
        # Wrap in split pane with close button
        pane = SplitPaneWidget(tab_widget)
        pane.apply_theme(self.dark_mode)
        pane.close_requested.connect(self._on_pane_close_requested)
        self.split_panes.append(pane)
        self.splitter.addWidget(pane)
        
        # Hide close button if only one pane
        self._update_close_buttons()
        
        # Set as active
        self.active_tab_widget = tab_widget
        
        return tab_widget
    
    def eventFilter(self, obj, event):
        """Track mouse clicks on tab bars to set active widget."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonPress:
            # Find which tab widget this tab bar belongs to
            for tw in self.tab_widgets:
                if tw.tabBar() == obj:
                    self.active_tab_widget = tw
                    break
        return super().eventFilter(obj, event)
    
    def _set_active_tab_widget(self, tw: EditorTabWidget):
        """Set the active tab widget when user interacts with it."""
        self.active_tab_widget = tw
    
    def transfer_tab(self, from_widget: EditorTabWidget, to_widget: EditorTabWidget, tab_index: int):
        """Transfer a tab from one widget to another."""
        if from_widget == to_widget:
            return
        
        tab = from_widget.remove_tab_without_close(tab_index)
        if tab:
            to_widget.receive_tab(tab)
    
    def _update_close_buttons(self):
        """Show/hide close buttons based on number of panes."""
        show = len(self.split_panes) > 1
        for pane in self.split_panes:
            pane.header.setVisible(show)
    
    def _on_pane_close_requested(self, pane: SplitPaneWidget):
        """Handle close button click on a pane."""
        if len(self.split_panes) <= 1:
            return
        
        # Check for unsaved changes
        for tab in pane.tab_widget.tabs:
            if tab.is_modified:
                reply = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"'{tab.name}' has unsaved changes. Close anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
        
        self.tab_widgets.remove(pane.tab_widget)
        self.split_panes.remove(pane)
        pane.deleteLater()
        self._update_close_buttons()
    
    def _remove_tab_widget(self, tab_widget: EditorTabWidget):
        """Remove a tab widget when all its tabs are closed."""
        if len(self.tab_widgets) <= 1:
            # Keep at least one tab open in the last pane
            tab_widget.new_tab()
            return
        
        # Find and remove the pane
        for pane in self.split_panes:
            if pane.tab_widget == tab_widget:
                self.tab_widgets.remove(tab_widget)
                self.split_panes.remove(pane)
                pane.deleteLater()
                break
        self._update_close_buttons()
    
    def current_tab_widget(self) -> Optional[EditorTabWidget]:
        """Get the currently focused tab widget."""
        # First check if we have a tracked active widget
        if self.active_tab_widget and self.active_tab_widget in self.tab_widgets:
            return self.active_tab_widget
        
        # Fall back to focus-based detection
        focus = QApplication.focusWidget()
        for tw in self.tab_widgets:
            if tw.isAncestorOf(focus) or tw == focus:
                self.active_tab_widget = tw
                return tw
        
        # Default to first tab widget
        if self.tab_widgets:
            self.active_tab_widget = self.tab_widgets[0]
            return self.active_tab_widget
        return None
    
    def current_tab(self) -> Optional[EditorTab]:
        """Get the current tab from the focused tab widget."""
        tw = self.current_tab_widget()
        return tw.current_tab() if tw else None
    
    def current_editor(self) -> Optional[TextEditor]:
        """Get the current editor."""
        tab = self.current_tab()
        return tab.editor if tab else None
    
    def split_horizontal(self):
        """Split the view horizontally."""
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self._add_tab_widget()
    
    def split_vertical(self):
        """Split the view vertically."""
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self._add_tab_widget()
    
    def close_split(self):
        """Close the current split pane."""
        if len(self.split_panes) <= 1:
            return
        
        tw = self.current_tab_widget()
        if tw:
            # Find the pane for this tab widget
            for pane in self.split_panes:
                if pane.tab_widget == tw:
                    self._on_pane_close_requested(pane)
                    break
    
    def new_file(self):
        """Create a new file in the current tab widget."""
        tw = self.current_tab_widget()
        if tw:
            tw.new_tab()
    
    def open_file(self, file_path: Path, content: str, encoding: str = "utf-8"):
        """Open a file in the current tab widget."""
        tw = self.current_tab_widget()
        if tw:
            tw.open_file(file_path, content, encoding)
    
    def save_current(self) -> bool:
        """Save the current file."""
        tw = self.current_tab_widget()
        return tw.save_current() if tw else False
    
    def save_current_as(self) -> bool:
        """Save the current file with a new name."""
        tw = self.current_tab_widget()
        return tw.save_current_as() if tw else False
    
    def set_dark_mode(self, enabled: bool):
        """Apply dark mode to all tab widgets."""
        self.dark_mode = enabled
        for tw in self.tab_widgets:
            tw.set_dark_mode(enabled)
        for pane in self.split_panes:
            pane.apply_theme(enabled)
        
        if enabled:
            self.splitter.setStyleSheet("QSplitter::handle { background-color: #3d3d3d; }")
        else:
            self.splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")


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
        self.open_project_action = file_menu.addAction("Open Pro&ject...")
        self.close_project_action = file_menu.addAction("Close Projec&t")
        
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
        
        view_menu.addSeparator()
        self.split_horizontal_action = view_menu.addAction("Split &Horizontal")
        self.split_vertical_action = view_menu.addAction("Split &Vertical")
        self.close_split_action = view_menu.addAction("Close Spli&t")
        
        view_menu.addSeparator()
        self.dark_mode_action = view_menu.addAction("&Dark Mode")
        self.dark_mode_action.setCheckable(True)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        self.about_action = help_menu.addAction("&About")


class MenuTabBar(QWidget):
    """Tab bar with File, Edit, View menus embedded in the app window."""
    
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self.main_window = main_window
        self.dark_mode = False
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(0)
        
        self.file_btn = QPushButton("File")
        self.edit_btn = QPushButton("Edit")
        self.view_btn = QPushButton("View")
        
        for btn in [self.file_btn, self.edit_btn, self.view_btn]:
            btn.setFlat(True)
            btn.setFixedHeight(26)
            btn.setFixedWidth(60)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        self.file_btn.clicked.connect(self._show_file_menu)
        self.edit_btn.clicked.connect(self._show_edit_menu)
        self.view_btn.clicked.connect(self._show_view_menu)
        
        self.apply_theme(False)
    
    def _show_file_menu(self):
        menu = QMenu(self)
        mm = self.main_window.menu_manager
        menu.addAction(mm.new_action)
        menu.addAction(mm.open_action)
        menu.addAction(mm.save_action)
        menu.addAction(mm.save_as_action)
        menu.addSeparator()
        menu.addAction(mm.open_project_action)
        menu.addAction(mm.close_project_action)
        menu.addSeparator()
        menu.addAction(mm.exit_action)
        self._apply_menu_theme(menu)
        menu.exec(self.file_btn.mapToGlobal(self.file_btn.rect().bottomLeft()))
    
    def _show_edit_menu(self):
        menu = QMenu(self)
        mm = self.main_window.menu_manager
        menu.addAction(mm.undo_action)
        menu.addAction(mm.redo_action)
        menu.addSeparator()
        menu.addAction(mm.cut_action)
        menu.addAction(mm.copy_action)
        menu.addAction(mm.paste_action)
        menu.addSeparator()
        menu.addAction(mm.select_all_action)
        menu.addAction(mm.select_line_action)
        menu.addAction(mm.select_word_action)
        self._apply_menu_theme(menu)
        menu.exec(self.edit_btn.mapToGlobal(self.edit_btn.rect().bottomLeft()))
    
    def _show_view_menu(self):
        menu = QMenu(self)
        mm = self.main_window.menu_manager
        menu.addAction(mm.find_action)
        menu.addAction(mm.find_replace_action)
        menu.addSeparator()
        menu.addAction(mm.split_horizontal_action)
        menu.addAction(mm.split_vertical_action)
        menu.addAction(mm.close_split_action)
        menu.addSeparator()
        menu.addAction(mm.dark_mode_action)
        self._apply_menu_theme(menu)
        menu.exec(self.view_btn.mapToGlobal(self.view_btn.rect().bottomLeft()))
    
    def _apply_menu_theme(self, menu):
        if self.dark_mode:
            menu.setStyleSheet("""
                QMenu { background-color: #2d2d2d; color: #ffffff; }
                QMenu::item:selected { background-color: #3d3d3d; }
            """)
    
    def apply_theme(self, dark_mode: bool):
        self.dark_mode = dark_mode
        if dark_mode:
            self.setStyleSheet("""
                QWidget { background-color: #2d2d2d; }
                QPushButton { 
                    color: #ffffff; 
                    background-color: #2d2d2d; 
                    border: none; 
                    padding: 5px 15px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #3d3d3d; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background-color: #f0f0f0; }
                QPushButton { 
                    color: #000000; 
                    background-color: #f0f0f0; 
                    border: none; 
                    padding: 5px 15px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #e0e0e0; }
            """)


class FileTreeExplorer(QDockWidget):
    """File system tree explorer with collapsible folders."""
    
    file_opened = pyqtSignal(str)
    
    def __init__(self, main_window: QMainWindow):
        super().__init__("Explorer", main_window)
        self.main_window = main_window
        self.dark_mode = False
        self.root_path = None
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.no_project_label = QLabel("No project open")
        self.no_project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.no_project_label)
        
        self.open_project_btn = QPushButton("Open Project")
        self.open_project_btn.clicked.connect(self.open_project)
        self.open_project_btn.setMaximumWidth(150)
        placeholder_layout.addWidget(self.open_project_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.hideColumn(1)
        self.tree.hideColumn(2)
        self.tree.hideColumn(3)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setVisible(False)
        
        self.container_layout.addWidget(self.placeholder)
        self.container_layout.addWidget(self.tree)
        
        self.setWidget(self.container)
        self.setMinimumWidth(200)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                        QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        self.apply_theme(False)
    
    def open_project(self):
        """Open a folder as a project."""
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder")
        if folder:
            self.set_root_path(folder)
    
    def _on_double_click(self, index: QModelIndex):
        """Handle double-click to open files."""
        file_path = self.model.filePath(index)
        if self.model.isDir(index):
            return
        self.file_opened.emit(file_path)
    
    def _show_context_menu(self, position):
        """Show right-click context menu."""
        index = self.tree.indexAt(position)
        menu = QMenu(self)
        
        new_file_action = menu.addAction("New File")
        new_folder_action = menu.addAction("New Folder")
        menu.addSeparator()
        
        rename_action = None
        delete_action = None
        if index.isValid():
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")
            menu.addSeparator()
        
        refresh_action = menu.addAction("Refresh")
        menu.addSeparator()
        open_project_action = menu.addAction("Open Project...")
        close_project_action = menu.addAction("Close Project")
        
        if self.dark_mode:
            menu.setStyleSheet("""
                QMenu { background-color: #2d2d2d; color: #ffffff; }
                QMenu::item:selected { background-color: #3d3d3d; }
            """)
        
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == new_file_action:
            self._create_new_file(index)
        elif action == new_folder_action:
            self._create_new_folder(index)
        elif action == rename_action and rename_action:
            self._rename_item(index)
        elif action == delete_action and delete_action:
            self._delete_item(index)
        elif action == refresh_action:
            self._refresh()
        elif action == open_project_action:
            self.open_project()
        elif action == close_project_action:
            self.close_project()
    
    def _get_directory_path(self, index: QModelIndex) -> str:
        """Get directory path from index (or parent if file)."""
        if not index.isValid():
            return self.root_path
        path = self.model.filePath(index)
        if self.model.isDir(index):
            return path
        return str(Path(path).parent)
    
    def _create_new_file(self, index: QModelIndex):
        """Create a new file."""
        dir_path = self._get_directory_path(index)
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if ok and name:
            file_path = Path(dir_path) / name
            try:
                file_path.touch()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file: {e}")
    
    def _create_new_folder(self, index: QModelIndex):
        """Create a new folder."""
        dir_path = self._get_directory_path(index)
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            folder_path = Path(dir_path) / name
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")
    
    def _rename_item(self, index: QModelIndex):
        """Rename a file or folder."""
        if not index.isValid():
            return
        old_path = Path(self.model.filePath(index))
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_path.name)
        if ok and new_name and new_name != old_path.name:
            new_path = old_path.parent / new_name
            try:
                old_path.rename(new_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename: {e}")
    
    def _delete_item(self, index: QModelIndex):
        """Delete a file or folder."""
        if not index.isValid():
            return
        path = Path(self.model.filePath(index))
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{path.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def _refresh(self):
        """Refresh the file tree."""
        self.model.setRootPath("")
        self.model.setRootPath(self.root_path)
    
    def highlight_file(self, file_path: str):
        """Highlight and scroll to a file in the tree."""
        if not file_path:
            return
        index = self.model.index(file_path)
        if index.isValid():
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)
    
    def set_root_path(self, path: str):
        """Change the root directory."""
        self.root_path = path
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.placeholder.setVisible(False)
        self.tree.setVisible(True)
        self.setWindowTitle(f"Explorer - {Path(path).name}")
    
    def close_project(self):
        """Close the current project."""
        self.root_path = None
        self.tree.setVisible(False)
        self.placeholder.setVisible(True)
        self.setWindowTitle("Explorer")
    
    def apply_theme(self, dark_mode: bool):
        """Apply dark or light theme."""
        self.dark_mode = dark_mode
        if dark_mode:
            self.setStyleSheet("""
                QDockWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QDockWidget::title {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 5px;
                }
                QWidget {
                    background-color: #2d2d2d;
                    color: #d4d4d4;
                }
                QLabel {
                    color: #d4d4d4;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QTreeView {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: none;
                }
                QTreeView::item:selected {
                    background-color: #3d3d3d;
                }
                QTreeView::item:hover {
                    background-color: #353535;
                }
            """)
        else:
            self.setStyleSheet("""
                QDockWidget {
                    background-color: #f5f5f5;
                }
                QDockWidget::title {
                    background-color: #e0e0e0;
                    padding: 5px;
                }
                QWidget {
                    background-color: #f5f5f5;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #cccccc;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QTreeView {
                    background-color: #ffffff;
                    border: none;
                }
                QTreeView::item:selected {
                    background-color: #cce8ff;
                }
                QTreeView::item:hover {
                    background-color: #e5f3ff;
                }
            """)


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
    """Dialog for find/replace operations across all open files."""
    
    def __init__(self, parent: QMainWindow, find_only: bool = False):
        super().__init__(parent)
        self.main_window = parent
        self.find_only = find_only
        self.dark_mode = getattr(parent, 'dark_mode', False)
        if find_only:
            self.setWindowTitle("Find (All Files)")
        else:
            self.setWindowTitle("Find & Replace (All Files)")
        self.setup_ui()
        self._apply_theme()
    
    def get_all_editors(self) -> list:
        """Get all open editors from all tab widgets."""
        editors = []
        for tw in self.main_window.editor_pane.tab_widgets:
            for tab in tw.tabs:
                editors.append((tab, tab.editor))
        return editors
    
    def get_current_editor(self) -> Optional[TextEditor]:
        """Get the current text editor from the editor pane."""
        return self.main_window.editor_pane.current_editor()
    
    def closeEvent(self, event):
        """Clear highlights when dialog is closed."""
        self._clear_all_highlights()
        super().closeEvent(event)
    
    def _clear_all_highlights(self):
        """Remove all search highlights from all editors."""
        for tab, editor in self.get_all_editors():
            editor.highlight_current_line()
    
    def _highlight_matches_in_editor(self, editor: TextEditor, matches: list):
        """Highlight matches in a specific editor."""
        extra_selections = []
        
        # Keep current line highlight only for focused editor
        current_editor = self.get_current_editor()
        if editor == current_editor and not editor.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            if editor.dark_mode:
                line_color = QColor("#3d3d3d")
            else:
                line_color = QColor("#e6f3ff")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = editor.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        # Add match highlights
        if editor.dark_mode:
            highlight_color = QColor("#806000")
        else:
            highlight_color = QColor("#ffff00")
        
        for start, end in matches:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(highlight_color)
            cursor = editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
            selection.cursor = cursor
            extra_selections.append(selection)
        
        editor.setExtraSelections(extra_selections)
    
    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout()
        
        # Find section
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.find_all)  # Live search as you type
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)
        
        # Replace section
        self.replace_widget = QWidget()
        replace_layout = QHBoxLayout(self.replace_widget)
        replace_layout.setContentsMargins(0, 0, 0, 0)
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addWidget(self.replace_widget)
        
        if self.find_only:
            self.replace_widget.setVisible(False)
        
        # Options
        self.case_sensitive = QCheckBox("Case Sensitive")
        self.whole_word = QCheckBox("Whole Word")
        self.regex = QCheckBox("Regular Expression")
        
        # Re-run search when options change
        self.case_sensitive.stateChanged.connect(self.find_all)
        self.whole_word.stateChanged.connect(self.find_all)
        self.regex.stateChanged.connect(self.find_all)
        
        layout.addWidget(self.case_sensitive)
        layout.addWidget(self.whole_word)
        layout.addWidget(self.regex)
        
        # Buttons
        button_layout = QHBoxLayout()
        find_button = QPushButton("Find All")
        find_button.clicked.connect(self.find_all)
        
        self.replace_button = QPushButton("Replace All")
        self.replace_button.clicked.connect(self.replace_all)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(find_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        if self.find_only:
            self.replace_button.setVisible(False)
        
        self.setLayout(layout)
        self.setMinimumWidth(400)
    
    def _apply_theme(self):
        """Apply dark or light theme to the dialog."""
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #2d2d2d; color: #d4d4d4; }
                QLabel { color: #d4d4d4; }
                QLineEdit { 
                    background-color: #1e1e1e; 
                    color: #d4d4d4; 
                    border: 1px solid #3d3d3d; 
                    padding: 5px; 
                }
                QCheckBox { color: #d4d4d4; }
                QCheckBox::indicator { 
                    border: 1px solid #555555; 
                    background-color: #2d2d2d; 
                }
                QCheckBox::indicator:checked { 
                    background-color: #0078d4; 
                }
                QPushButton { 
                    background-color: #3d3d3d; 
                    color: #d4d4d4; 
                    border: 1px solid #555555; 
                    padding: 6px 12px; 
                }
                QPushButton:hover { background-color: #4d4d4d; }
            """)
        else:
            self.setStyleSheet("")
    
    def find_all(self):
        """Find all occurrences across all open files and highlight them."""
        pattern = self.find_input.text()
        if not pattern:
            self._clear_all_highlights()
            self.setWindowTitle("Find & Replace (All Files)")
            return
        
        case_sensitive = self.case_sensitive.isChecked()
        whole_word = self.whole_word.isChecked()
        use_regex = self.regex.isChecked()
        
        total_matches = 0
        files_with_matches = 0
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            
            if use_regex:
                regex = re.compile(pattern, flags)
            else:
                escaped = re.escape(pattern)
                if whole_word:
                    escaped = r'\b' + escaped + r'\b'
                regex = re.compile(escaped, flags)
            
            for tab, editor in self.get_all_editors():
                text = editor.toPlainText()
                results = []
                
                for match in regex.finditer(text):
                    results.append(match.span())
                
                if results:
                    files_with_matches += 1
                    total_matches += len(results)
                
                self._highlight_matches_in_editor(editor, results)
                
        except re.error:
            pass
        
        self.setWindowTitle(f"Find & Replace - {total_matches} match(es) in {files_with_matches} file(s)")
    
    def replace_all(self):
        """Replace all occurrences across all open files."""
        pattern = self.find_input.text()
        replacement = self.replace_input.text()
        
        if not pattern:
            return
        
        # Warn if replacement text is empty
        if not replacement:
            reply = QMessageBox.warning(
                self, "Empty Replacement",
                "The replacement text is empty. This will delete all matches.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        case_sensitive = self.case_sensitive.isChecked()
        whole_word = self.whole_word.isChecked()
        use_regex = self.regex.isChecked()
        
        total_count = 0
        files_modified = 0
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            
            if use_regex:
                regex = re.compile(pattern, flags)
            else:
                escaped = re.escape(pattern)
                if whole_word:
                    escaped = r'\b' + escaped + r'\b'
                regex = re.compile(escaped, flags)
            
            for tab, editor in self.get_all_editors():
                text = editor.toPlainText()
                new_text, count = regex.subn(replacement, text)
                if count > 0:
                    editor.setPlainText(new_text)
                    tab.is_modified = True
                    total_count += count
                    files_modified += 1
                    
        except re.error:
            pass
        
        # Clear highlights and show result
        self._clear_all_highlights()
        self.setWindowTitle(f"Find & Replace - Replaced {total_count} in {files_modified} file(s)")


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
        self.dark_mode = False
        
        # Create editor pane (with tabs and split support)
        self.editor_pane = EditorPane(self.settings_manager)
        
        # Initialize UI managers
        self.menu_manager = MenuManager(self)
        self.menu_tab_bar = MenuTabBar(self)
        
        # Create file tree explorer
        self.file_explorer = FileTreeExplorer(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_explorer)
        self.file_explorer.file_opened.connect(self._open_file_from_explorer)
        
        # Create central widget with menu tab bar and editor pane
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.menu_tab_bar)
        central_layout.addWidget(self.editor_pane)
        self.setCentralWidget(central_widget)
        
        # Status bar (will update based on current editor)
        self.status_bar = self.statusBar()
        self.position_label = QLabel("Line 1, Column 1")
        self.status_bar.addWidget(self.position_label)
        self.encoding_label = QLabel("UTF-8")
        self.status_bar.addPermanentWidget(self.encoding_label)
        
        # Connect to tab changes to update status bar
        for tw in self.editor_pane.tab_widgets:
            tw.tab_changed.connect(self._on_tab_changed)
        
        # Connect menu actions
        self._connect_actions()
        
        # Setup window
        self.setWindowTitle("Text Editor")
        self.resize(
            self.settings_manager.get("window_width", 1000),
            self.settings_manager.get("window_height", 700)
        )
        
        # Apply saved dark mode setting
        dark_mode = self.settings_manager.get("dark_mode", False)
        if dark_mode:
            self.menu_manager.dark_mode_action.setChecked(True)
            self.toggle_dark_mode(True)
    
    def _on_tab_changed(self, tab: EditorTab):
        """Update UI when tab changes."""
        self._update_title()
        self._connect_current_editor()
    
    def _connect_current_editor(self):
        """Connect signals from current editor."""
        editor = self.editor_pane.current_editor()
        if editor:
            try:
                editor.cursorPositionChanged.disconnect(self._update_position)
            except:
                pass
            editor.cursorPositionChanged.connect(self._update_position)
            self._update_position()
    
    def _update_position(self):
        """Update cursor position in status bar."""
        editor = self.editor_pane.current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            column = cursor.positionInBlock() + 1
            self.position_label.setText(f"Line {line}, Column {column}")
    
    def _connect_actions(self):
        """Connect menu actions to functions."""
        # File menu
        self.menu_manager.new_action.triggered.connect(self.new_file)
        self.menu_manager.open_action.triggered.connect(self.open_file)
        self.menu_manager.save_action.triggered.connect(self.save_file)
        self.menu_manager.save_as_action.triggered.connect(self.save_as_file)
        self.menu_manager.open_project_action.triggered.connect(self.file_explorer.open_project)
        self.menu_manager.close_project_action.triggered.connect(self.file_explorer.close_project)
        self.menu_manager.exit_action.triggered.connect(self.close)
        
        # Edit menu
        self.menu_manager.undo_action.triggered.connect(self._undo)
        self.menu_manager.redo_action.triggered.connect(self._redo)
        self.menu_manager.cut_action.triggered.connect(self._cut)
        self.menu_manager.copy_action.triggered.connect(self._copy)
        self.menu_manager.paste_action.triggered.connect(self._paste)
        self.menu_manager.select_all_action.triggered.connect(self._select_all)
        self.menu_manager.select_line_action.triggered.connect(self._select_line)
        self.menu_manager.select_word_action.triggered.connect(self._select_word)
        
        # View menu
        self.menu_manager.find_action.triggered.connect(self.show_find_dialog)
        self.menu_manager.find_replace_action.triggered.connect(self.show_find_replace_dialog)
        self.menu_manager.split_horizontal_action.triggered.connect(self.editor_pane.split_horizontal)
        self.menu_manager.split_vertical_action.triggered.connect(self.editor_pane.split_vertical)
        self.menu_manager.close_split_action.triggered.connect(self.editor_pane.close_split)
        self.menu_manager.dark_mode_action.triggered.connect(self.toggle_dark_mode)
    
    def _undo(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.undo()
    
    def _redo(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.redo()
    
    def _cut(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.cut()
    
    def _copy(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.copy()
    
    def _paste(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.paste()
    
    def _select_all(self):
        editor = self.editor_pane.current_editor()
        if editor:
            editor.selectAll()
    
    def _select_line(self):
        editor = self.editor_pane.current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.select(cursor.SelectionType.LineUnderCursor)
            editor.setTextCursor(cursor)
    
    def _select_word(self):
        editor = self.editor_pane.current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            editor.setTextCursor(cursor)
    
    def toggle_dark_mode(self, checked: bool):
        """Toggle between dark and light mode."""
        self.editor_pane.set_dark_mode(checked)
        self.settings_manager.set("dark_mode", checked)
        self._apply_window_theme(checked)
    
    def _apply_window_theme(self, dark_mode: bool):
        """Apply theme to window elements."""
        self.dark_mode = dark_mode
        self.menu_tab_bar.apply_theme(dark_mode)
        self.file_explorer.apply_theme(dark_mode)
        if dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #2d2d2d; }
                QMenuBar { background-color: #2d2d2d; color: #d4d4d4; }
                QMenuBar::item:selected { background-color: #3d3d3d; }
                QMenu { background-color: #2d2d2d; color: #d4d4d4; }
                QMenu::item:selected { background-color: #3d3d3d; }
                QStatusBar { background-color: #2d2d2d; color: #d4d4d4; }
                QDialog { background-color: #2d2d2d; color: #d4d4d4; }
                QMessageBox { background-color: #2d2d2d; color: #d4d4d4; }
                QInputDialog { background-color: #2d2d2d; color: #d4d4d4; }
                QLabel { color: #d4d4d4; }
                QLineEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3d3d3d; padding: 5px; }
                QCheckBox { color: #d4d4d4; }
                QPushButton { background-color: #3d3d3d; color: #d4d4d4; border: 1px solid #555555; padding: 6px 12px; }
                QPushButton:hover { background-color: #4d4d4d; }
                QFileDialog { background-color: #2d2d2d; color: #d4d4d4; }
            """)
        else:
            self.setStyleSheet("")
    
    def new_file(self):
        """Create a new file in a new tab."""
        self.editor_pane.new_file()
        self._update_title()
    
    def open_file(self):
        """Open a file in a new tab."""
        file_path, _ = QFileDialog.getOpenFileName(self)
        if not file_path:
            return
        
        self._open_file_path(file_path)
    
    def _open_file_path(self, file_path: str):
        """Open a file by path in a new tab."""
        content, success = self.file_manager.read_file(Path(file_path))
        
        if success:
            self.editor_pane.open_file(Path(file_path), content, self.file_manager.encoding)
            self._update_title()
            self.encoding_label.setText(self.file_manager.encoding.upper())
            
            # Add to recent files
            recent = self.settings_manager.get("recent_files", [])
            if file_path in recent:
                recent.remove(file_path)
            recent.insert(0, file_path)
            self.settings_manager.set("recent_files", recent[:10])
            self.file_explorer.highlight_file(file_path)
        else:
            QMessageBox.critical(self, "Error", content)
    
    def _open_file_from_explorer(self, file_path: str):
        """Open a file from the file explorer."""
        self._open_file_path(file_path)
    
    def save_file(self):
        """Save current file."""
        if self.editor_pane.save_current():
            self._update_title()
    
    def save_as_file(self):
        """Save file with a new name."""
        if self.editor_pane.save_current_as():
            self._update_title()
    
    def show_find_dialog(self):
        """Show find dialog (find only, no replace)."""
        dialog = FindReplaceDialog(self, find_only=True)
        dialog.exec()
    
    def show_find_replace_dialog(self):
        """Show find and replace dialog."""
        dialog = FindReplaceDialog(self)
        dialog.exec()
    
    def _update_title(self):
        """Update window title based on current tab."""
        tab = self.editor_pane.current_tab()
        if tab:
            self.setWindowTitle(f"Text Editor - {tab.display_name}")
        else:
            self.setWindowTitle("Text Editor")
    
    def closeEvent(self, event):
        """Handle window close."""
        # Check all tabs for unsaved changes
        for tw in self.editor_pane.tab_widgets:
            for tab in tw.tabs:
                if tab.is_modified:
                    reply = QMessageBox.question(
                        self, "Unsaved Changes",
                        f"'{tab.name}' has unsaved changes. Exit anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
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
