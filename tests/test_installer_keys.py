"""The installer's dialogs open on a control; the arrows step every ring.

The three confirmation dialogs used to open on a neutral focus sink, which
keeb reserves for main windows: a dialog was opened to do one thing, so it
opens on its first control. The arrows were dead in every installer surface,
the neutral start included; they now walk the same ring Tab walks.
"""

from __future__ import annotations

import sys
from pathlib import Path

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
)

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "installer"
if str(INSTALLER_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALLER_DIR))

import installer_legacy as legacy  # noqa: E402
import installer_keys as keys  # noqa: E402
from installer_legacy_dialog import LegacyCleanupDialog  # noqa: E402
from installer_widgets import (  # noqa: E402
    AppRunningDialog,
    LicenceDialog,
    UninstallDialog,
)

STEPS = 4
_PLAN = legacy.LegacyPlan(
    version="3.0.0",
    folder=Path("C:/old"),
    registration=True,
    shortcuts=(Path("C:/old/a.lnk"),),
    left_alone=(),
)


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def ring(app: QApplication):
    installed = keys.install_arrow_ring(app)
    yield installed
    app.removeEventFilter(installed)


def _open(dialog: QDialog, app: QApplication) -> QDialog:
    dialog.show()
    dialog.activateWindow()
    app.processEvents()
    return dialog


@pytest.mark.parametrize(
    ("make", "expected"),
    [
        (lambda: AppRunningDialog("install"), "Cancel"),
        (lambda: UninstallDialog(), "Cancel"),
        (lambda: LegacyCleanupDialog(_PLAN), f"Keep {legacy.LEGACY_APP_NAME}"),
        (lambda: LicenceDialog("text\n" * 200, "Licence"), "Close"),
    ],
)
def test_each_dialog_opens_on_its_first_control(
    app: QApplication, make, expected: str
) -> None:
    dialog = _open(make(), app)
    try:
        focused = dialog.focusWidget()
        assert isinstance(focused, QPushButton) and focused.text() == expected
        assert dialog.first_stop() is focused
    finally:
        dialog.close()


def test_a_dialog_with_nothing_to_focus_opens_on_nothing(app: QApplication) -> None:
    dialog = keys.FirstStopDialog()
    _open(dialog, app)
    try:
        assert dialog.first_stop() is None
    finally:
        dialog.close()


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


@pytest.mark.parametrize(
    "make",
    [lambda: UninstallDialog(), lambda: LicenceDialog("text\n" * 200, "Licence")],
)
def test_the_arrows_walk_the_tab_ring(app: QApplication, ring, make) -> None:
    dialog = _open(make(), app)
    try:
        assert _walk(dialog, Qt.Key.Key_Right, app) == _walk(
            dialog, Qt.Key.Key_Tab, app
        )
        assert _walk(dialog, Qt.Key.Key_Left, app) == _walk(
            dialog, Qt.Key.Key_Backtab, app
        )
    finally:
        dialog.close()


def _form(app: QApplication, first) -> QDialog:
    dialog = keys.FirstStopDialog()
    layout = QVBoxLayout(dialog)
    layout.addWidget(first)
    layout.addWidget(QPushButton("OK"))
    _open(dialog, app)
    first.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    return dialog


def test_a_text_field_keeps_its_arrows(app: QApplication, ring) -> None:
    field = QLineEdit("abc")
    dialog = _form(app, field)
    try:
        field.setCursorPosition(0)
        QTest.keyClick(field, Qt.Key.Key_Right)
        assert dialog.focusWidget() is field and field.cursorPosition() == 1
    finally:
        dialog.close()


def test_a_pane_that_scrolls_sideways_keeps_its_arrows(app: QApplication, ring) -> None:
    pane = QTextEdit()
    pane.setReadOnly(True)
    pane.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    pane.setPlainText("x" * 2000)
    dialog = _form(app, pane)
    try:
        QTest.keyClick(pane, Qt.Key.Key_Right)
        assert dialog.focusWidget() is pane
    finally:
        dialog.close()


def test_only_unmodified_arrow_presses_at_the_focused_widget_are_taken(
    app: QApplication,
) -> None:
    dialog = _form(app, QPushButton("first"))
    focused = dialog.focusWidget()
    filt = keys.ArrowRing()

    def press(key, mods=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
        return QKeyEvent(QEvent.Type.KeyPress, key, mods)

    try:
        release = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Right, Qt.NoModifier)
        assert not filt.eventFilter(focused, release)
        assert not filt.eventFilter(focused, press(Qt.Key.Key_Down))
        shift = Qt.KeyboardModifier.ShiftModifier
        assert not filt.eventFilter(focused, press(Qt.Key.Key_Left, shift))
        assert not filt.eventFilter(dialog, press(Qt.Key.Key_Right))
        assert filt.eventFilter(focused, press(Qt.Key.Key_Right))
    finally:
        dialog.close()
