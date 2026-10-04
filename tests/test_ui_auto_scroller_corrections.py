"""The two later scroller corrections, over BOTH copies of the scroller.

Stellody's, ported through postal-gambit 1.6.0: opening focus is not a reader;
a surface frozen beneath a modal takes no input at all. The fixtures and
helpers live in `scroller_harness`.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from scroller_harness import (
    FROZEN_TICKS,
    HAND_POSITION,
    LONG_TEXT,
    MODAL_POSITION,
    attach,
    close_modal,
    hand_events,
    open_modal,
    reading,
    run_ticks,
    ticks_for,
)

pytest_plugins = ["scroller_harness"]


def test_focus_arriving_inside_after_the_hold_is_a_reader(
    scroller_module, long_pane
) -> None:
    """Watched at the application, with an ancestry test, once the surface is open."""
    module = scroller_module
    scroller = reading(module, long_pane)
    scroller._on_focus_changed(None, long_pane.viewport())
    assert scroller._phase is module.Phase.MANUAL

    for elsewhere in (None, QWidget()):
        scroller._phase = module.Phase.DOWN
        scroller._on_focus_changed(None, elsewhere)
        assert scroller._phase is module.Phase.DOWN


def test_the_start_hold_survives_the_opening_focus(scroller_module, long_pane) -> None:
    """A dialog focusing its text as it opens is not a reader taking hold."""
    module = scroller_module
    scroller = attach(module, long_pane)
    scroller._on_focus_changed(None, long_pane)
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) - 1)
    scroller._on_focus_changed(None, long_pane)
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN, "the full hold, not the manual one"


def test_the_opening_flag_clears_with_the_hold_not_the_first_step(
    scroller_module, long_pane
) -> None:
    """A reader arriving between the hold's end and the first pixel is seen."""
    module = scroller_module
    scroller = attach(module, long_pane)
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS))
    assert scroller._phase is module.Phase.DOWN
    assert long_pane.verticalScrollBar().value() == 0, "not one step taken yet"
    scroller._on_focus_changed(None, long_pane)
    assert scroller._phase is module.Phase.MANUAL


def test_a_modal_above_freezes_the_surface_in_time(
    scroller_module, long_pane, qt_app
) -> None:
    """Frozen, not suspended: the hold that was running is still running."""
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    bar.setValue(MODAL_POSITION)
    scroller._phase = module.Phase.PAUSE_BOTTOM
    scroller._wait_ms = module.BOTTOM_HOLD_MS
    modal = open_modal(qt_app)
    assert scroller._is_frozen() is True

    run_ticks(scroller, FROZEN_TICKS)
    assert bar.value() == MODAL_POSITION
    assert scroller._phase is module.Phase.PAUSE_BOTTOM
    assert scroller._wait_ms == module.BOTTOM_HOLD_MS
    close_modal(modal, qt_app)
    assert scroller._is_frozen() is False


def test_a_frozen_surface_takes_no_input_at_all(
    scroller_module, long_pane, qt_app
) -> None:
    """Wheel, click, key, scrollbar and focus beneath a modal are no reader."""
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    scroller._phase = module.Phase.PAUSE_BOTTOM
    scroller._wait_ms = module.BOTTOM_HOLD_MS
    modal = open_modal(qt_app)

    for watched, event in hand_events(long_pane):
        scroller.eventFilter(watched, event)
    bar.sliderPressed.emit()
    bar.sliderMoved.emit(HAND_POSITION)
    bar.sliderReleased.emit()
    scroller._on_focus_changed(None, long_pane)
    assert scroller._phase is module.Phase.PAUSE_BOTTOM
    assert scroller._wait_ms == module.BOTTOM_HOLD_MS
    close_modal(modal, qt_app)


def test_a_reset_while_frozen_is_followed_not_read_as_a_hand(
    scroller_module, long_pane, qt_app
) -> None:
    """The toolkit returning the view to the top is no reader; carry on from it.

    The position is read afresh on every tick and never recorded, so it is
    followed while frozen by construction; this keeps it that way.
    """
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    bar.setValue(HAND_POSITION)
    modal = open_modal(qt_app)
    bar.setValue(bar.minimum())
    close_modal(modal, qt_app)

    assert scroller._phase is module.Phase.DOWN
    run_ticks(scroller, module.TICKS_PER_DESCENT)
    assert bar.value() == bar.minimum() + module.DESCENT_PX


def test_a_modal_that_owns_the_surface_does_not_freeze_it(
    scroller_module, qt_app
) -> None:
    """The modal's OWN surfaces are exactly the ones that should still read."""
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    inner = QTextBrowser(dialog)
    inner.setPlainText(LONG_TEXT)
    layout.addWidget(inner)
    layout.addWidget(QPushButton("Close", dialog))
    dialog.setModal(True)
    dialog.show()
    qt_app.processEvents()
    scroller = attach(scroller_module, inner)
    assert QApplication.activeModalWidget() is dialog
    assert scroller._is_frozen() is False
    dialog.close()
