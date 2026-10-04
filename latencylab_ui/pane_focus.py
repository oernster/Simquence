from __future__ import annotations

"""A reading pane is a keyboard stop only while it has somewhere to scroll.

Ported from NarrateX `pane_focus.py`, with the Resize resync of Stellody's
ReadingPane folded in.

A pane is chrome, not a control: it holds content rather than being something
to act on. Qt gives the whole scroll area family StrongFocus by default, so a
click anywhere in a licence, the Guide or the run output focused the pane; the
dialogs opened on it too.

Two changes; the first is what a reader notices:

TabFocus rather than StrongFocus, so a CLICK never focuses it. Even Tab reaching
it paints nothing, since the theme rings no text view in any state.

Then the stop itself is conditional. A page that fits its viewport scrolls
nowhere, so it drops off the ring entirely; a page that overflows keeps the
stop, because a long text with no controls of its own could not be read from
the keyboard otherwise. It is re-decided every time either scrollbar's range
changes (content loaded) and on every resize (the same page overflows or not
according to how the window is sized). The viewport is a separate focusable
child and is never a stop.

A dialog must not OPEN on a reading pane either; see first_stop_dialog.py.
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QWidget


class OverflowFocus(QObject):
    """Keeps one scroll area a TabFocus stop exactly while it overflows."""

    def __init__(self, area: QAbstractScrollArea) -> None:
        super().__init__(area)
        self._area = area
        area.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        area.installEventFilter(self)
        for bar in (area.verticalScrollBar(), area.horizontalScrollBar()):
            bar.rangeChanged.connect(self.sync)
        self.sync()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        """Resizing changes whether the content still fits, so re-decide."""

        if event.type() == QEvent.Type.Resize:
            self.sync()
        return False

    def overflows(self) -> bool:
        return (
            self._area.verticalScrollBar().maximum() > 0
            or self._area.horizontalScrollBar().maximum() > 0
        )

    def sync(self, *_range: int) -> None:
        """A stop while it scrolls somewhere; never a stop when it does not."""

        self._area.setFocusPolicy(
            Qt.FocusPolicy.TabFocus if self.overflows() else Qt.FocusPolicy.NoFocus
        )


def as_pane(widget: QWidget) -> QWidget:
    """Mark `widget` as chrome: it holds controls and is never a keyboard stop.

    A scroll area's viewport is a second focusable child, so for a scroll area
    both are set; a plain QWidget or QFrame is NoFocus already and saying so at
    construction keeps the intent in the code rather than in the defaults.
    """

    widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if isinstance(widget, QAbstractScrollArea):
        widget.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return widget


def follow_overflow(area: QAbstractScrollArea) -> OverflowFocus:
    """Make `area` a stop exactly while it overflows; the area owns the helper."""

    return OverflowFocus(area)
