"""Shared harness for the reading-cycle tests, over BOTH copies of the scroller.

The application and the setup program each carry a copy, since the installer
imports nothing from `simquence_ui`; every cycle test runs against both, so
the copies cannot drift (postal-gambit's pattern). Test modules load this as a
pytest plugin, so the fixtures below are defined once.

Real time is never waited on. Each scroller's own timer is stopped first, after
asserting it was running, since a timer that never starts would otherwise pass
everything; then the tick is called by hand.
"""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QDialog, QTextBrowser

from simquence_ui import auto_scroller as app_scroller

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "installer"
if str(INSTALLER_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALLER_DIR))

# The installer's modules are flat and top level, so its directory must be on
# the path first; importing by name afterwards keeps every import at the top.
installer_scroller = importlib.import_module("installer_reading_pane")

# Enough text that the pane must overflow whatever the offscreen metrics are.
LONG_TEXT = "\n".join(f"line {n}" for n in range(400))
PANE_W = 200
PANE_H = 80
FITS_SIZE = 400
DESCENT_TICKS = 20
FROZEN_TICKS = 50
HAND_POSITION = 50
MODAL_POSITION = 30
# One notch of a mouse wheel, in eighths of a degree.
WHEEL_NOTCH = 120


@pytest.fixture()
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(params=[app_scroller, installer_scroller], ids=["app", "installer"])
def scroller_module(request):
    return request.param


@pytest.fixture()
def long_pane(qt_app: QApplication):
    widget = QTextBrowser()
    widget.setPlainText(LONG_TEXT)
    widget.resize(PANE_W, PANE_H)
    widget.show()
    qt_app.processEvents()
    assert widget.verticalScrollBar().maximum() > 0, "the pane must overflow"
    yield widget
    widget.close()


def attach(module, area):
    """Attach, prove the timer was running, then take the clock by hand."""
    scroller = module.AutoScroller(area)
    assert scroller._timer.isActive()
    assert scroller._timer.interval() == module.TICK_MS
    scroller._timer.stop()
    return scroller


def run_ticks(scroller, count: int) -> None:
    for _ in range(count):
        scroller._tick()


def ticks_for(module, milliseconds: int) -> int:
    """Ticks until a hold of this length is spent, rounding up."""
    return math.ceil(milliseconds / module.TICK_MS)


def reading(module, pane):
    """A scroller already past its start hold, descending from the top."""
    scroller = attach(module, pane)
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS))
    assert scroller._phase is module.Phase.DOWN
    return scroller


def open_modal(app: QApplication) -> QDialog:
    modal = QDialog()
    modal.setModal(True)
    modal.show()
    app.processEvents()
    assert QApplication.activeModalWidget() is modal
    return modal


def close_modal(modal: QDialog, app: QApplication) -> None:
    modal.close()
    app.processEvents()
    assert QApplication.activeModalWidget() is None


def hand_events(pane) -> tuple:
    """A wheel and a click for the viewport, a key press for the widget."""
    origin = QPointF(0, 0)
    wheel = QWheelEvent(
        origin,
        origin,
        QPoint(0, 0),
        QPoint(0, -WHEEL_NOTCH),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    click = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        origin,
        origin,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    key = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    return ((pane.viewport(), wheel), (pane.viewport(), click), (pane, key))
