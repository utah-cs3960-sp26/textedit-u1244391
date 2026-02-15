"""
Tests for MultiCursorManager and RectangularSelectionManager.
Run with: python test_multicursor.py
"""

import unittest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QTextCursor

from textEditor import TextEditor, MultiCursorManager, RectangularSelectionManager


# Create QApplication once for all tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMultiCursorManager(unittest.TestCase):
    """Tests for MultiCursorManager functionality."""
    
    def setUp(self):
        """Create a fresh TextEditor for each test."""
        self.editor = TextEditor()
        self.editor.setPlainText("line one\nline two\nline three\nline four\nline five")
    
    def test_initial_state(self):
        """Multi-cursor manager should start inactive."""
        self.assertFalse(self.editor.multi_cursor_manager.active)
        self.assertFalse(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 0)
    
    def test_add_cursor(self):
        """Adding a cursor should activate multi-cursor mode."""
        cursor = self.editor.textCursor()
        cursor.setPosition(5)
        self.editor.multi_cursor_manager.add_cursor(cursor)
        
        self.assertTrue(self.editor.multi_cursor_manager.active)
        self.assertTrue(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 1)
    
    def test_add_multiple_cursors(self):
        """Should be able to add multiple cursors."""
        for pos in [5, 15, 25]:
            cursor = self.editor.textCursor()
            cursor.setPosition(pos)
            self.editor.multi_cursor_manager.add_cursor(cursor)
        
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 3)
    
    def test_no_duplicate_cursors(self):
        """Should not add duplicate cursors at same position."""
        cursor1 = self.editor.textCursor()
        cursor1.setPosition(10)
        self.editor.multi_cursor_manager.add_cursor(cursor1)
        
        cursor2 = self.editor.textCursor()
        cursor2.setPosition(10)
        self.editor.multi_cursor_manager.add_cursor(cursor2)
        
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 1)
    
    def test_clear_cursors(self):
        """Clearing should remove all extra cursors."""
        cursor = self.editor.textCursor()
        cursor.setPosition(5)
        self.editor.multi_cursor_manager.add_cursor(cursor)
        
        self.editor.multi_cursor_manager.clear()
        
        self.assertFalse(self.editor.multi_cursor_manager.active)
        self.assertFalse(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 0)
    
    def test_get_all_cursors_includes_main(self):
        """get_all_cursors should include main cursor plus extras."""
        cursor = self.editor.textCursor()
        cursor.setPosition(5)
        self.editor.multi_cursor_manager.add_cursor(cursor)
        
        all_cursors = self.editor.multi_cursor_manager.get_all_cursors()
        
        # Main cursor + 1 extra
        self.assertEqual(len(all_cursors), 2)
    
    def test_add_cursor_above(self):
        """Should add cursor on line above."""
        # Position main cursor on line 3
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Down)
        cursor.movePosition(QTextCursor.MoveOperation.Down)
        self.editor.setTextCursor(cursor)
        
        self.editor.multi_cursor_manager.add_cursor_above()
        
        self.assertTrue(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 1)
    
    def test_add_cursor_below(self):
        """Should add cursor on line below."""
        self.editor.multi_cursor_manager.add_cursor_below()
        
        self.assertTrue(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 1)


class TestRectangularSelectionManager(unittest.TestCase):
    """Tests for RectangularSelectionManager functionality."""
    
    def setUp(self):
        """Create a fresh TextEditor for each test."""
        self.editor = TextEditor()
        self.editor.setPlainText("line one\nline two\nline three\nline four\nline five")
    
    def test_initial_state(self):
        """Rectangular selection should start inactive."""
        self.assertFalse(self.editor.rect_selection_manager.active)
        self.assertIsNone(self.editor.rect_selection_manager.start_pos)
        self.assertIsNone(self.editor.rect_selection_manager.end_pos)
    
    def test_start_selection(self):
        """Starting selection should set start position."""
        self.editor.rect_selection_manager.start_selection(1, 5)
        
        self.assertTrue(self.editor.rect_selection_manager.active)
        self.assertEqual(self.editor.rect_selection_manager.start_pos, (1, 5))
        self.assertEqual(self.editor.rect_selection_manager.end_pos, (1, 5))
    
    def test_update_selection(self):
        """Updating selection should change end position."""
        self.editor.rect_selection_manager.start_selection(1, 5)
        self.editor.rect_selection_manager.update_selection(3, 10)
        
        self.assertEqual(self.editor.rect_selection_manager.end_pos, (3, 10))
    
    def test_clear_selection(self):
        """Clearing should reset all state."""
        self.editor.rect_selection_manager.start_selection(1, 5)
        self.editor.rect_selection_manager.update_selection(3, 10)
        self.editor.rect_selection_manager.clear()
        
        self.assertFalse(self.editor.rect_selection_manager.active)
        self.assertIsNone(self.editor.rect_selection_manager.start_pos)
        self.assertIsNone(self.editor.rect_selection_manager.end_pos)
    
    def test_get_selection_range_normalized(self):
        """Selection range should be normalized (min to max)."""
        # Select from bottom-right to top-left
        self.editor.rect_selection_manager.start_selection(3, 10)
        self.editor.rect_selection_manager.update_selection(1, 2)
        
        range_info = self.editor.rect_selection_manager.get_selection_range()
        start_line, end_line, start_col, end_col = range_info
        
        self.assertEqual(start_line, 1)
        self.assertEqual(end_line, 3)
        self.assertEqual(start_col, 2)
        self.assertEqual(end_col, 10)
    
    def test_get_selection_range_inactive(self):
        """Should return None when inactive."""
        self.assertIsNone(self.editor.rect_selection_manager.get_selection_range())
    
    def test_get_selected_text(self):
        """Should extract text from rectangular region."""
        # Select columns 0-4 on lines 0-2
        self.editor.rect_selection_manager.start_selection(0, 0)
        self.editor.rect_selection_manager.update_selection(2, 4)
        
        selected = self.editor.rect_selection_manager.get_selected_text()
        
        self.assertEqual(len(selected), 3)
        self.assertEqual(selected[0], "line")
        self.assertEqual(selected[1], "line")
        self.assertEqual(selected[2], "line")
    
    def test_create_cursors_from_selection(self):
        """Should create multiple cursors from rectangular selection."""
        self.editor.rect_selection_manager.start_selection(0, 5)
        self.editor.rect_selection_manager.update_selection(3, 5)
        
        self.editor.rect_selection_manager.create_cursors_from_selection(
            self.editor.multi_cursor_manager
        )
        
        # Should have cursors on 4 lines (0, 1, 2, 3)
        # Main cursor + 3 extra
        self.assertTrue(self.editor.multi_cursor_manager.has_cursors())
        self.assertEqual(len(self.editor.multi_cursor_manager.cursors), 3)
        
        # Rectangular selection should be cleared
        self.assertFalse(self.editor.rect_selection_manager.active)


class TestMultiCursorEditing(unittest.TestCase):
    """Tests for actual editing with multiple cursors."""
    
    def setUp(self):
        """Create a fresh TextEditor for each test."""
        self.editor = TextEditor()
        self.editor.setPlainText("line one\nline two\nline three\nline four\nline five")
    
    def test_insert_at_multiple_cursors(self):
        """Inserting text should appear at all cursor positions."""
        # Set main cursor at start of line 1
        cursor = self.editor.textCursor()
        cursor.setPosition(0)
        self.editor.setTextCursor(cursor)
        
        # Add cursor at start of line 2 (position 9, after "line one\n")
        cursor2 = self.editor.textCursor()
        cursor2.setPosition(9)
        self.editor.multi_cursor_manager.add_cursor(cursor2)
        
        # Insert text at extra cursors
        self.editor._multi_cursor_insert("X")
        
        text = self.editor.toPlainText()
        lines = text.split('\n')
        
        # Line 2 should have X at start
        self.assertTrue(lines[1].startswith("X"))
    
    def test_delete_at_multiple_cursors(self):
        """Deleting should work at all cursor positions."""
        # Position cursors after first char of lines 1 and 2
        cursor = self.editor.textCursor()
        cursor.setPosition(1)  # After 'l' in first line
        self.editor.setTextCursor(cursor)
        
        cursor2 = self.editor.textCursor()
        cursor2.setPosition(10)  # After 'l' in second line
        self.editor.multi_cursor_manager.add_cursor(cursor2)
        
        # Delete at extra cursors
        self.editor._multi_cursor_delete(backwards=True)
        
        text = self.editor.toPlainText()
        lines = text.split('\n')
        
        # Second line should now start with 'i' instead of 'l'
        self.assertTrue(lines[1].startswith("i"))


class TestHighlighting(unittest.TestCase):
    """Tests for cursor highlighting."""
    
    def setUp(self):
        """Create a fresh TextEditor for each test."""
        self.editor = TextEditor()
        self.editor.setPlainText("line one\nline two\nline three\nline four\nline five")
    
    def test_multi_cursor_highlights_added(self):
        """Extra cursors should be highlighted."""
        cursor = self.editor.textCursor()
        cursor.setPosition(5)
        self.editor.multi_cursor_manager.add_cursor(cursor)
        
        extra_selections = []
        self.editor.multi_cursor_manager.highlight_cursors(extra_selections, dark_mode=False)
        
        self.assertEqual(len(extra_selections), 1)
    
    def test_rect_selection_highlights_added(self):
        """Rectangular selection should be highlighted."""
        self.editor.rect_selection_manager.start_selection(0, 0)
        self.editor.rect_selection_manager.update_selection(2, 4)
        
        extra_selections = []
        self.editor.rect_selection_manager.highlight_selection(extra_selections, dark_mode=False)
        
        # Should have highlights for 3 lines
        self.assertEqual(len(extra_selections), 3)


if __name__ == "__main__":
    print("Running Multicursor and Rectangular Selection Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
