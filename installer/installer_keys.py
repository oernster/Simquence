"""The installer's keyboard model: dialogs open on a control; arrows step rings.

A STANDALONE COPY of the application's `simquence_ui/first_stop_dialog.py` and
`simquence_ui/dialog_ring.py`, for the reason `installer_reading_pane` gives:
the installer runs with only `installer/` on the path and cannot import
`simquence_ui`. The rules are the application's; change both copies together.

The window itself still starts neutral (`NeutralStart`); a dialog does the
opposite, because it was opened on purpose to do the one thing it is for.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QLineEdit,
    QWidget,
)

_ARROWS = {Qt.Key.Key_Right: True, Qt.Key.Key_Left: False}
_TEXT_ENTRY_TYPES = (QLineEdit, QAbstractSpinBox)


def is_reading_pane_class(widget_class: type) -> bool:
    """A scroll area that is read rather than acted on: not a list or table."""

    return issubclass(widget_class, QAbstractScrollArea) and not issubclass(
        widget_class, QAbstractItemView
    )


class FirstStopDialog(QDialog):
    """A dialog whose first control is focused the moment it is shown.

    Walked along Qt's own focus chain, so the answer is what the first Tab would
    have reached; a reading pane is passed over, so a licence opens on Close.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._first_stop_applied = False

    def first_stop(self) -> QWidget | None:
        widget = self.nextInFocusChain()
        seen: set[int] = set()
        while widget is not None and id(widget) not in seen:
            seen.add(id(widget))
            if self._is_stop(widget):
                return widget
            widget = widget.nextInFocusChain()
        return None

    def _is_stop(self, widget: QWidget) -> bool:
        return (
            widget is not self
            and self.isAncestorOf(widget)
            and widget.isEnabled()
            and widget.isVisible()
            and not is_reading_pane_class(type(widget))
            and bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)
        )

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._first_stop_applied:
            return
        self._first_stop_applied = True
        target = self.first_stop()
        if target is not None:
            target.setFocus(Qt.FocusReason.TabFocusReason)


def _owns_horizontal_arrows(widget: QWidget) -> bool:
    """A text field keeps them for the caret; a sideways-scrolling pane, to scroll."""

    cur: QWidget | None = widget
    while cur is not None:
        if isinstance(cur, _TEXT_ENTRY_TYPES):
            return True
        if is_reading_pane_class(type(cur)):
            return cur.horizontalScrollBar().maximum() > 0
        cur = cur.parentWidget()
    return False


class ArrowRing(QObject):
    """Application-wide: Right steps the focused window's ring forward, Left back.

    Every installer window and dialog, the neutral start included, so the first
    Right on a freshly opened setup window enters the ring just as Tab does.
    """

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if event.type() != QEvent.Type.KeyPress:
            return False
        forward = _ARROWS.get(event.key())
        if forward is None or event.modifiers() != Qt.KeyboardModifier.NoModifier:
            return False
        # Once, at the widget the key was meant for, not again at each parent
        # it propagates to. Qt never delivers to None, so neither is None here.
        focused = watched
        if focused is not QApplication.focusWidget():
            return False
        if _owns_horizontal_arrows(focused):
            return False
        focused.window().focusNextPrevChild(forward)
        return True


def install_arrow_ring(app: QApplication) -> ArrowRing:
    """Install once per application; the caller keeps the returned filter."""

    ring = ArrowRing(app)
    app.installEventFilter(ring)
    return ring
