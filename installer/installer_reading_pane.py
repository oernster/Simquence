"""The installer's reading pane: the licence text reads itself and takes no click.

A STANDALONE COPY of the application's `simquence_ui/auto_scroller.py` and
`simquence_ui/pane_focus.py`, as Fulcrum's installer carries its own copy of
Fulcrum's scroller. It cannot import them: the installer's modules are flat and
top level, run with only `installer/` on the path; the editable install maps
`simquence` alone (`simquence_ui` is excluded from the distribution), so
`import simquence_ui` from here raises ModuleNotFoundError (measured). The
constants and the cycle are the application's; change both copies together.

Only pixel-scrolling surfaces may wear the scroller: the licence is a QTextEdit,
which scrolls in pixels, never a QPlainTextEdit, which scrolls in lines.
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QPlainTextEdit,
    QWidget,
)

TICK_MS = 40
START_HOLD_MS = 5000
DESCENT_PX = 1
TICKS_PER_DESCENT = 2
BOTTOM_HOLD_MS = 5000
REWIND_PX = 15
TOP_HOLD_MS = 2000
MANUAL_RESUME_MS = 2500


def refuse_line_scrolling(area: QAbstractScrollArea) -> None:
    """Refuse a QPlainTextEdit outright: its scrollbar counts lines, not pixels."""

    if isinstance(area, QPlainTextEdit):
        raise TypeError(
            "a QPlainTextEdit scrolls in lines; give the text a QTextBrowser"
        )


class Phase(Enum):
    DOWN = auto()
    PAUSE_BOTTOM = auto()
    UP = auto()
    PAUSE_TOP = auto()
    MANUAL = auto()


class AutoScroller(QObject):
    """Drives one scrollable surface through the reading cycle.

    Holds still on open, descends slowly, holds at the end, rewinds fast and
    repeats. Manual input suspends it, never disables it; a modal above the
    surface freezes it in place and a frozen surface takes no input. Focus
    arriving during the start hold is the dialog opening, not a reader, so it
    is ignored until that hold is spent.
    """

    def __init__(self, area: QAbstractScrollArea) -> None:
        refuse_line_scrolling(area)
        super().__init__(area)
        self._area = area
        self._phase = Phase.PAUSE_TOP
        self._wait_ms = START_HOLD_MS
        self._ticks_to_step = TICKS_PER_DESCENT
        self._opening = True

        area.viewport().installEventFilter(self)
        area.installEventFilter(self)

        bar = area.verticalScrollBar()
        bar.sliderPressed.connect(self._suspend)
        bar.sliderReleased.connect(self._suspend)
        bar.sliderMoved.connect(lambda _value: self._suspend())

        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus_changed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    def _suspend(self) -> None:
        """Hand the surface to the reader for a while; never while frozen."""
        if self._is_frozen():
            return
        self._phase = Phase.MANUAL
        self._wait_ms = MANUAL_RESUME_MS

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if event.type() in (
            event.Type.Wheel,
            event.Type.MouseButtonPress,
            event.Type.KeyPress,
        ):
            self._suspend()
        return super().eventFilter(watched, event)

    def _on_focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        if self._opening:
            return
        if new is not None and (new is self._area or self._area.isAncestorOf(new)):
            self._suspend()

    def _is_frozen(self) -> bool:
        modal = QApplication.activeModalWidget()
        if modal is None:
            return False
        return not (modal is self._area.window() or modal.isAncestorOf(self._area))

    def _tick(self) -> None:
        bar = self._area.verticalScrollBar()
        if bar is None or bar.maximum() == 0:
            return
        if self._is_frozen():
            return

        if self._wait_ms > 0:
            self._wait_ms -= TICK_MS
            if self._wait_ms > 0:
                return
            self._opening = False
            self._phase = self._phase_after_wait(bar)
            return

        if self._phase == Phase.DOWN:
            self._descend(bar)
        elif self._phase == Phase.UP:
            self._rewind(bar)

    def _phase_after_wait(self, bar) -> Phase:
        if self._phase == Phase.PAUSE_BOTTOM:
            return Phase.UP
        if self._phase == Phase.MANUAL and bar.value() >= bar.maximum():
            return Phase.UP
        return Phase.DOWN

    def _descend(self, bar) -> None:
        self._ticks_to_step -= 1
        if self._ticks_to_step > 0:
            return
        self._ticks_to_step = TICKS_PER_DESCENT

        if bar.value() >= bar.maximum():
            self._phase = Phase.PAUSE_BOTTOM
            self._wait_ms = BOTTOM_HOLD_MS
            return
        bar.setValue(bar.value() + DESCENT_PX)

    def _rewind(self, bar) -> None:
        if bar.value() <= bar.minimum():
            self._phase = Phase.PAUSE_TOP
            self._wait_ms = TOP_HOLD_MS
            return
        bar.setValue(bar.value() - REWIND_PX)


class OverflowFocus(QObject):
    """A TabFocus stop exactly while the pane overflows; never a click stop.

    The viewport is a separate focusable child and is never a stop. Re-decided
    on either scrollbar's range change and on every resize.
    """

    def __init__(self, area: QAbstractScrollArea) -> None:
        super().__init__(area)
        self._area = area
        area.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        area.installEventFilter(self)
        for bar in (area.verticalScrollBar(), area.horizontalScrollBar()):
            bar.rangeChanged.connect(self.sync)
        self.sync()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if event.type() == QEvent.Type.Resize:
            self.sync()
        return False

    def overflows(self) -> bool:
        return (
            self._area.verticalScrollBar().maximum() > 0
            or self._area.horizontalScrollBar().maximum() > 0
        )

    def sync(self, *_range: int) -> None:
        self._area.setFocusPolicy(
            Qt.FocusPolicy.TabFocus if self.overflows() else Qt.FocusPolicy.NoFocus
        )


def reading_pane(area: QAbstractScrollArea) -> QAbstractScrollArea:
    """Give `area` the reading cycle and the overflow-only Tab stop."""

    AutoScroller(area)
    OverflowFocus(area)
    return area
