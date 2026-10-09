"""The reading cycle, driven tick by tick, over BOTH copies of the scroller.

The fixtures and helpers live in `scroller_harness`, shared with the tests of
the two later corrections in `test_ui_auto_scroller_corrections.py`.
"""

from __future__ import annotations

import pytest

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from scroller_harness import (
    DESCENT_TICKS,
    FITS_SIZE,
    HAND_POSITION,
    LONG_TEXT,
    PANE_H,
    PANE_W,
    app_scroller,
    attach,
    hand_events,
    installer_scroller,
    reading,
    run_ticks,
    ticks_for,
)

pytest_plugins = ["scroller_harness"]

# How far below a pixel surface a line surface travels, at the least.
PIXELS_PER_LINE_FLOOR = 5


def test_the_constants_are_kept_identical_in_both_copies() -> None:
    names = (
        "TICK_MS",
        "START_HOLD_MS",
        "DESCENT_PX",
        "TICKS_PER_DESCENT",
        "BOTTOM_HOLD_MS",
        "REWIND_PX",
        "TOP_HOLD_MS",
        "MANUAL_RESUME_MS",
    )
    for name in names:
        assert getattr(app_scroller, name) == getattr(installer_scroller, name)


def test_every_reading_surface_scrolls_in_pixels(qt_app) -> None:
    """A QPlainTextEdit counts LINES, so the pixel pace would race on it.

    The same one-unit step that reads as a gentle drift on a pixel-scrolling
    widget becomes a whole line jumping; the fast rewind becomes fifteen lines
    a tick. That is how three of these dialogs once shipped, reported as jerky.
    """
    from simquence_ui.about_dialog import AboutDialog, AboutDialogContent
    from simquence_ui.guide_dialog import GuideDialog
    from simquence_ui.how_to_read_dialog import HowToReadDialog
    from simquence_ui.licence_dialog import LicenceDialog
    from simquence_ui.main_licence_dialog import MainLicenceDialog

    host = QWidget()
    QVBoxLayout(host)
    host.show()
    qt_app.processEvents()
    content = AboutDialogContent(title="Simquence", body="<p>x</p>")
    dialogs = [
        GuideDialog(host),
        HowToReadDialog(host),
        LicenceDialog(host),
        MainLicenceDialog(host),
        AboutDialog(host, content=content),
    ]
    for dialog in dialogs:
        panes = dialog.findChildren(QTextEdit)
        assert panes, f"{type(dialog).__name__} has no pixel-scrolling pane"
        for found in panes:
            assert not isinstance(found, QPlainTextEdit)
        # Reading through is what these dialogs are for, so each one reads itself.
        readers = [p for p in panes if p.findChildren(app_scroller.AutoScroller)]
        assert readers, f"{type(dialog).__name__} has no self-reading pane"
        dialog.close()
    host.close()
    qt_app.processEvents()


def test_a_line_scrolling_surface_is_refused(scroller_module, qt_app) -> None:
    lines = QPlainTextEdit()
    with pytest.raises(TypeError):
        scroller_module.AutoScroller(lines)
    assert not lines.findChildren(scroller_module.AutoScroller)


def test_a_pixel_surface_travels_far_further_than_a_line_surface(qt_app) -> None:
    """The measurement behind the rule above, so the number is not folklore."""
    by_lines = QPlainTextEdit()
    by_lines.setPlainText(LONG_TEXT)
    by_pixels = QTextBrowser()
    by_pixels.setPlainText(LONG_TEXT)
    for widget in (by_lines, by_pixels):
        widget.resize(PANE_W, PANE_H)
        widget.show()
    qt_app.processEvents()
    lines = by_lines.verticalScrollBar().maximum()
    assert by_pixels.verticalScrollBar().maximum() > lines * PIXELS_PER_LINE_FLOOR
    for widget in (by_lines, by_pixels):
        widget.close()


def test_a_fresh_surface_holds_still_before_it_reads(
    scroller_module, long_pane
) -> None:
    module = scroller_module
    scroller = attach(module, long_pane)
    bar = long_pane.verticalScrollBar()
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) - 1)
    assert bar.value() == 0
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN
    assert bar.value() == 0


def test_the_descent_is_half_pace_and_the_rewind_is_not(
    scroller_module, long_pane
) -> None:
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    run_ticks(scroller, DESCENT_TICKS)
    assert bar.value() == DESCENT_TICKS // module.TICKS_PER_DESCENT

    # From the bottom, so the step has room rather than clamping at zero.
    scroller._phase = module.Phase.UP
    bar.setValue(bar.maximum())
    before = bar.value()
    run_ticks(scroller, 1)
    assert before - bar.value() == module.REWIND_PX


def test_the_cycle_turns_round_at_both_ends(scroller_module, long_pane) -> None:
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    bar.setValue(bar.maximum())
    run_ticks(scroller, module.TICKS_PER_DESCENT)
    assert scroller._phase is module.Phase.PAUSE_BOTTOM

    run_ticks(scroller, ticks_for(module, module.BOTTOM_HOLD_MS) - 1)
    assert bar.value() == bar.maximum(), "the tail is held for reading"
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.UP

    run_ticks(scroller, bar.maximum() // module.REWIND_PX + 1)
    assert bar.value() == bar.minimum()
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.PAUSE_TOP

    run_ticks(scroller, ticks_for(module, module.TOP_HOLD_MS))
    assert scroller._phase is module.Phase.DOWN


def test_reading_by_hand_suspends_then_resumes_in_place(
    scroller_module, long_pane
) -> None:
    """Taking over never switches the feature off, nor rewinds to the top."""
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    bar.setValue(HAND_POSITION)
    scroller._suspend()
    assert scroller._phase is module.Phase.MANUAL

    run_ticks(scroller, ticks_for(module, module.MANUAL_RESUME_MS) - 1)
    assert bar.value() == HAND_POSITION, "nothing moves while the reader has it"
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN
    run_ticks(scroller, module.TICKS_PER_DESCENT)
    assert bar.value() == HAND_POSITION + module.DESCENT_PX


def test_a_manual_pause_at_the_very_bottom_rewinds(scroller_module, long_pane) -> None:
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    bar.setValue(bar.maximum())
    scroller._suspend()
    run_ticks(scroller, ticks_for(module, module.MANUAL_RESUME_MS))
    assert scroller._phase is module.Phase.UP


def test_wheel_click_and_key_suspend_and_nothing_else_does(
    scroller_module, long_pane
) -> None:
    """The viewport sees the wheel and clicks; the widget sees the keys."""
    module = scroller_module
    scroller = reading(module, long_pane)
    for watched, event in hand_events(long_pane):
        scroller._phase = module.Phase.DOWN
        assert scroller.eventFilter(watched, event) is False
        assert scroller._phase is module.Phase.MANUAL

    scroller._phase = module.Phase.DOWN
    scroller.eventFilter(long_pane, QEvent(QEvent.Type.Show))
    assert scroller._phase is module.Phase.DOWN


def test_the_scrollbar_counts_as_reading_by_hand(scroller_module, long_pane) -> None:
    module = scroller_module
    scroller = reading(module, long_pane)
    bar = long_pane.verticalScrollBar()
    for signal in (bar.sliderPressed, bar.sliderReleased):
        scroller._phase = module.Phase.DOWN
        signal.emit()
        assert scroller._phase is module.Phase.MANUAL
    scroller._phase = module.Phase.DOWN
    bar.sliderMoved.emit(HAND_POSITION)
    assert scroller._phase is module.Phase.MANUAL


def test_a_surface_that_fits_costs_nothing(scroller_module, qt_app) -> None:
    module = scroller_module
    short = QTextBrowser()
    short.setPlainText("one line")
    short.resize(FITS_SIZE, FITS_SIZE)
    short.show()
    qt_app.processEvents()
    scroller = attach(module, short)
    assert short.verticalScrollBar().maximum() == 0
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) * 2)
    assert scroller._phase is module.Phase.PAUSE_TOP, "the hold was never consumed"
    assert scroller._wait_ms == module.START_HOLD_MS
    short.close()


def test_the_scroller_changes_no_focus_policy(scroller_module, qt_app) -> None:
    """Focus is the reading pane's business; the scroller only watches it."""
    area = QTextBrowser()
    policies = (area.focusPolicy(), area.viewport().focusPolicy())
    attach(scroller_module, area)
    assert (area.focusPolicy(), area.viewport().focusPolicy()) == policies
