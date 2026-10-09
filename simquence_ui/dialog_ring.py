from __future__ import annotations

"""The horizontal arrows step every dialog's ring, as Tab and Shift+Tab do.

The main window's ring is driven by `FocusCycleController`, which only answers
keys from its own window. Inside a dialog Qt walks Tab natively and the arrows
were left to whichever control held focus: a licence's text kept Right for
itself while the composer's tree used it to expand a branch; the ring was
trapped in both. Right and Left are aliases for Tab and Shift+Tab at every
stop, so this hands them to the dialog's own Tab walk, which already skips
whatever Tab skips.

Three things keep their horizontal arrows (only three): a text field owns
them for the caret; an open menu owns them for its submenus (both decided once,
in `horizontal_arrow_belongs_elsewhere`); a reading pane that actually scrolls
sideways owns them for that axis; Tab leaves it.
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from simquence_ui.first_stop_dialog import is_reading_pane_class
from simquence_ui.focus_cycle_keys import horizontal_arrow_belongs_elsewhere

_ARROWS = {Qt.Key.Key_Right: True, Qt.Key.Key_Left: False}


def scrolls_sideways(widget: QWidget) -> bool:
    """Whether `widget` sits in a reading pane with a horizontal axis to scroll."""

    cur: QWidget | None = widget
    while cur is not None:
        if is_reading_pane_class(type(cur)):
            return cur.horizontalScrollBar().maximum() > 0
        cur = cur.parentWidget()
    return False


class DialogArrowRing(QObject):
    """Application-wide: Right steps a dialog's ring forward, Left back."""

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
        dialog = focused.window()
        if not isinstance(dialog, QDialog):
            return False
        if horizontal_arrow_belongs_elsewhere(forward=forward):
            return False
        if scrolls_sideways(focused):
            return False
        dialog.focusNextPrevChild(forward)
        return True


def install_dialog_arrow_ring(app: QApplication) -> DialogArrowRing:
    """Install once per application; the caller keeps the returned filter."""

    ring = DialogArrowRing(app)
    app.installEventFilter(ring)
    return ring
