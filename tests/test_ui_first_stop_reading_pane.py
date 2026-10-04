"""Which scroll areas a dialog must not open on, tested without a QApplication.

Ported from ClearBudget `tests/ui_logic/test_first_stop_reading_pane.py`. A
dialog opens on its first control. About, the Guide, How to Read and both
licences have a text view first, so each opened on the page instead of on OK.
Lists, tables and trees are also scroll areas yet are things to act on: the
Model Composer opens on its section tree and must keep doing so. The predicate
works on classes, so no QApplication is needed.
"""

from PySide6.QtWidgets import (
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTextBrowser,
    QTextEdit,
    QTreeView,
    QTreeWidget,
)

from latencylab_ui.first_stop_dialog import is_reading_pane_class


def test_text_and_page_scroll_areas_are_reading_panes() -> None:
    for widget_class in (QTextBrowser, QTextEdit, QPlainTextEdit, QScrollArea):
        assert is_reading_pane_class(widget_class), widget_class.__name__


def test_lists_tables_and_trees_stay_openable() -> None:
    for widget_class in (QTableWidget, QListWidget, QTreeView, QTreeWidget):
        assert not is_reading_pane_class(widget_class), widget_class.__name__


def test_a_control_is_not_a_pane() -> None:
    assert not is_reading_pane_class(QPushButton)
