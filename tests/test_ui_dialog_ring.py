"""The horizontal arrows step every dialog's ring, as Tab and Shift+Tab do.

Before this, a licence's text kept Right for itself and the composer's tree
used it to expand a branch, so the arrows were trapped in both. The tests walk
the same dialog with Tab and with Right and require the same stops.
"""

from __future__ import annotations

import pytest

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from simquence_ui.dialog_ring import (
    DialogArrowRing,
    install_dialog_arrow_ring,
    scrolls_sideways,
)
from simquence_ui.guide_dialog import GuideDialog
from simquence_ui.how_to_read_dialog import HowToReadDialog
from simquence_ui.licence_dialog import LicenceDialog
from simquence_ui.main_licence_dialog import MainLicenceDialog

STEPS = 5
READING_DIALOGS = (GuideDialog, HowToReadDialog, LicenceDialog, MainLicenceDialog)


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def ring(app: QApplication):
    installed = install_dialog_arrow_ring(app)
    yield installed
    app.removeEventFilter(installed)


@pytest.fixture()
def parent(app: QApplication) -> QWidget:
    widget = QWidget()
    widget.show()
    app.processEvents()
    yield widget
    widget.close()


def _open(dialog: QDialog, app: QApplication) -> QDialog:
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    return dialog


def _walk(dialog: QDialog, key: Qt.Key, app: QApplication) -> list[int]:
    start = dialog.focusWidget()
    stops = []
    for _ in range(STEPS):
        QTest.keyClick(dialog.focusWidget(), key)
        app.processEvents()
        stops.append(id(dialog.focusWidget()))
    start.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    return stops


@pytest.mark.parametrize("dialog_type", READING_DIALOGS)
def test_right_walks_the_tab_ring_and_left_the_shift_tab_ring(
    app: QApplication, ring, parent: QWidget, dialog_type
) -> None:
    dialog = _open(dialog_type(parent), app)
    try:
        assert _walk(dialog, Qt.Key.Key_Right, app) == _walk(
            dialog, Qt.Key.Key_Tab, app
        )
        assert _walk(dialog, Qt.Key.Key_Left, app) == _walk(
            dialog, Qt.Key.Key_Backtab, app
        )
    finally:
        dialog.close()


def _form(app: QApplication, first: QWidget) -> tuple[QDialog, QPushButton]:
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    layout.addWidget(first)
    button = QPushButton("OK")
    layout.addWidget(button)
    _open(dialog, app)
    first.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    return dialog, button


def test_a_text_field_keeps_its_arrows_for_the_caret(app: QApplication, ring) -> None:
    field = QLineEdit("abc")
    dialog, _ = _form(app, field)
    try:
        field.setCursorPosition(0)
        QTest.keyClick(field, Qt.Key.Key_Right)
        assert dialog.focusWidget() is field
        assert field.cursorPosition() == 1
    finally:
        dialog.close()


def test_a_pane_that_scrolls_sideways_keeps_its_arrows(app: QApplication, ring) -> None:
    pane = QTextEdit()
    pane.setReadOnly(True)
    pane.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    pane.setPlainText("x" * 2000)
    dialog, _ = _form(app, pane)
    try:
        assert scrolls_sideways(pane)
        QTest.keyClick(pane, Qt.Key.Key_Right)
        assert dialog.focusWidget() is pane
    finally:
        dialog.close()


def test_a_pane_that_fits_sideways_hands_the_arrows_to_the_ring(
    app: QApplication, ring
) -> None:
    pane = QTextEdit()
    pane.setReadOnly(True)
    pane.setPlainText("short")
    dialog, button = _form(app, pane)
    try:
        assert not scrolls_sideways(pane)
        QTest.keyClick(pane, Qt.Key.Key_Right)
        assert dialog.focusWidget() is button
    finally:
        dialog.close()


def test_a_widget_outside_any_reading_pane_does_not_scroll_sideways(
    app: QApplication,
) -> None:
    assert not scrolls_sideways(QPushButton())


def _press(key: Qt.Key, mods=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, mods)


def test_only_unmodified_arrow_presses_at_the_focused_widget_are_taken(
    app: QApplication, ring
) -> None:
    dialog, button = _form(app, QPushButton("first"))
    focused = dialog.focusWidget()
    filt = DialogArrowRing()
    try:
        release = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Right, Qt.NoModifier)
        assert not filt.eventFilter(focused, release)
        assert not filt.eventFilter(focused, _press(Qt.Key.Key_Up))
        shifted = _press(Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        assert not filt.eventFilter(focused, shifted)
        assert not filt.eventFilter(button, _press(Qt.Key.Key_Right))
        assert filt.eventFilter(focused, _press(Qt.Key.Key_Right))
    finally:
        dialog.close()


def test_a_window_that_is_not_a_dialog_is_left_to_its_own_ring(
    app: QApplication,
) -> None:
    window = QWidget()
    layout = QVBoxLayout(window)
    button = QPushButton("x")
    layout.addWidget(button)
    window.show()
    window.activateWindow()
    button.setFocus()
    app.processEvents()
    try:
        assert not DialogArrowRing().eventFilter(button, _press(Qt.Key.Key_Right))
    finally:
        window.close()
