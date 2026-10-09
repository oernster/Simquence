from __future__ import annotations

import pytest

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication, QWidget

from simquence_ui.main_window import MainWindow
from simquence_ui.theme import Theme, apply_theme, tokens_for

# Widths chosen either side of the default so centring is shown to be a property
# of the layout rather than of one lucky size.
WINDOW_WIDTHS = (900, 1400, 1920)

# Large enough that scaling leaves solid interior pixels rather than only the
# blended edges an icon this size is mostly made of.
ICON_PROBE_PX = 64

WINDOW_HEIGHT = 720

# Far narrower than the bar can be, so the window's own minimum decides.
NARROW_WINDOW_WIDTH = 300

# A badge one pixel off centre is not a defect; a badge 134 pixels off centre
# was the reported one. Half a pixel of rounding is all the slack there is.
CENTRING_TOLERANCE_PX = 1.0


class _IdleController(QObject):
    """A controller that never runs anything, so the window builds and stops."""

    started = Signal(int)
    succeeded = Signal(int, object)
    failed = Signal(int, str)
    cancelled = Signal(int, int)
    finished = Signal(int, float)

    def is_running(self) -> bool:
        return False

    def is_cancelled(self, run_token: int) -> bool:
        return False

    def shutdown(self) -> None:
        return None


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(app: QApplication) -> MainWindow:
    win = MainWindow(run_controller=_IdleController())
    win.show()
    app.processEvents()
    yield win
    win.close()


@pytest.mark.parametrize("width", WINDOW_WIDTHS)
def test_the_mark_is_centred_on_the_bar_not_on_the_leftover_space(
    app: QApplication, window: MainWindow, width: int
) -> None:
    """The reported defect, measured.

    The mark used to sit between two stretches, which centres it in the gap
    between the flanking control groups. Those groups are nowhere near the same
    width, so it landed 134px right of centre in a 1400px window.
    """

    window.resize(width, WINDOW_HEIGHT)
    app.processEvents()

    mark = window._distributions_btn
    bar = mark.parentWidget()
    mark_centre = mark.geometry().x() + mark.geometry().width() / 2

    assert abs(mark_centre - bar.width() / 2) <= CENTRING_TOLERANCE_PX


def test_a_band_with_no_centre_keeps_its_ordinary_minimum(app: QApplication) -> None:
    """Before the bar is told what it centres there is nothing to make room
    for, so it asks for no more than any widget would."""

    from simquence_ui.main_window_top_bar import NavBand

    holder = QWidget()
    band = NavBand(holder)
    assert band.minimumSizeHint() == QWidget.minimumSizeHint(band)
    holder.deleteLater()


def test_the_centred_mark_never_lands_on_a_side_group(
    app: QApplication, window: MainWindow
) -> None:
    """Centring on the bar ignores the groups beside it, so a narrow window
    drew the mark over the Edit button. Asked for far less than it needs, the
    window is held wide enough that nothing overlaps."""

    _enable_every_bar_control(window, app)
    window.resize(NARROW_WINDOW_WIDTH, WINDOW_HEIGHT)
    app.processEvents()

    band = window._top_bar
    mark = window._distributions_btn

    def drawn(widget: QWidget):
        return widget.rect().translated(widget.mapTo(band, widget.rect().topLeft()))

    others = [w for w in band.ring_stops() if w is not mark]
    assert others
    for widget in others:
        assert not drawn(mark).intersects(drawn(widget)), widget.objectName()


def test_the_mark_is_its_picture_and_not_a_font_glyph(
    window: MainWindow,
) -> None:
    """A glyph is whatever font happens to be installed; a file is the same
    everywhere."""

    mark = window._distributions_btn
    assert mark.text() == ""
    assert mark.icon().isNull() is False


def test_the_checked_mark_keeps_its_picture(window: MainWindow) -> None:
    """Checked says "on" with its fill, never by flattening the picture.

    Flattened to one dark ink the chart was measured reading as a mound; in
    full colour its outline keeps it a chart on the yellow fill.
    """

    icon = window._distributions_btn.icon()
    size = QSize(ICON_PROBE_PX, ICON_PROBE_PX)

    unchecked = icon.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off).toImage()
    checked = icon.pixmap(size, QIcon.Mode.Normal, QIcon.State.On).toImage()

    assert checked == unchecked


def test_the_centre_mark_is_the_distributions_toggle(window: MainWindow) -> None:
    """It was decoration; it is now the control. The mark is the most prominent
    thing on the bar and the panel it opens is the point of running anything, so
    the two belong together rather than competing from opposite ends."""

    mark = window._distributions_btn

    assert mark.isCheckable() is True
    assert mark.toolTip()
    # Not transparent to the mouse any more, plus on the keyboard ring, because
    # there is now something to do to it.
    assert mark.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) is False
    assert mark.focusPolicy() != Qt.FocusPolicy.NoFocus

    window._distributions_dock.setVisible(True)
    assert mark.isChecked() is True
    window._distributions_dock.setVisible(False)
    assert mark.isChecked() is False


def test_compose_button_is_reachable_and_is_not_a_toggle(window: MainWindow) -> None:
    """It was checkable while the composer was a dock sharing the window with
    the results, because the button was the only thing saying which of the two
    was up. A modal dialog IS the window while it is open, so a button
    reporting that from underneath it says nothing."""

    compose = window._compose_btn

    assert compose.isCheckable() is False
    assert compose.focusPolicy() != compose.focusPolicy().NoFocus

    window._model_composer.show()
    assert compose.isChecked() is False

    window._model_composer.reject()


def _band_stops(window: MainWindow) -> list:
    """The ring's stops that live on the top bar, in ring order."""

    from simquence_ui.focus_cycle_widgets import (
        collect_interactive_widgets_in_layout_order,
    )

    band = window._top_bar
    return [
        w
        for w in collect_interactive_widgets_in_layout_order(window)
        if band.isAncestorOf(w)
    ]


# The mark centres itself on the BAR, so where it falls relative to the group on
# the left is a function of the window width. Narrow enough and the group runs
# past the centre, which says nothing about the ring and everything about the
# window: these tests use a width the application is actually used at.
BAR_ORDER_WIDTH = 1400


def _enable_every_bar_control(window: MainWindow, app: QApplication) -> None:
    """Every control on the bar live, at a realistic width, laid out.

    Enabled because a disabled control is correctly off the ring, so an order
    measured with half the bar inert would be measuring the wrong list.
    """

    window.resize(BAR_ORDER_WIDTH, WINDOW_HEIGHT)
    for stop in window._top_bar.ring_stops():
        stop.setEnabled(True)
    for _ in range(3):
        window._top_bar.layout().activate()
        app.processEvents()


def test_the_ring_crosses_the_bar_left_to_right(
    app: QApplication, window: MainWindow
) -> None:
    """The mark is an OVERLAY, so layout order is not reading order.

    Centring it on the whole bar means putting it in the same grid cell as the
    row of buttons, which the layout then reaches last however far left it is
    drawn. Unfixed, the ring stepped from the leftmost button to the theme
    toggle at the far right and only then back to the mark in the middle, which
    is indistinguishable from the mark having been skipped.
    """

    _enable_every_bar_control(window, app)

    stops = _band_stops(window)
    centres = [w.mapTo(window, w.rect().center()).x() for w in stops]

    assert stops, "the bar contributes nothing to the ring"
    assert centres == sorted(centres), [
        (w.objectName() or type(w).__name__, x) for w, x in zip(stops, centres)
    ]


def test_the_mark_is_reached_before_the_control_to_its_right(
    app: QApplication, window: MainWindow
) -> None:
    """Stated separately from the ordering rule because this is the reported
    bug: the mark sits mid-bar and was offered after the rightmost control."""

    _enable_every_bar_control(window, app)

    stops = _band_stops(window)
    assert window._distributions_btn in stops
    assert stops.index(window._distributions_btn) < stops.index(window._theme_toggle)


def test_the_declared_order_holds_every_control_on_the_bar(
    app: QApplication, window: MainWindow
) -> None:
    """A hand-written order is one forgotten line from dropping a new button off
    the ring entirely, so it is checked against the band's real children."""

    from simquence_ui.focus_cycle_widgets import is_interactive_widget

    _enable_every_bar_control(window, app)
    band = window._top_bar
    declared = set(map(id, band.ring_stops()))

    missing = [
        child.objectName() or type(child).__name__
        for child in band.findChildren(QWidget)
        if is_interactive_widget(window, child) and id(child) not in declared
    ]
    assert not missing, missing


@pytest.mark.parametrize("theme", (Theme.DARK, Theme.LIGHT))
def test_distributions_button_looks_different_when_the_panel_is_open(
    app: QApplication, window: MainWindow, theme: Theme
) -> None:
    """Checked being SET is not the same as checked being SHOWN.

    A stylesheet with no rule for a button's checked state renders open and
    closed identically, which is a state nobody can see. Asserting the rendered
    pixels is the only way to tell the two apart.
    """

    apply_theme(app, theme)
    app.processEvents()

    button = window._distributions_btn
    accent = QColor(tokens_for(theme).accent).rgb()

    def accent_pixels() -> int:
        image = button.grab().toImage()
        return sum(
            1
            for y in range(image.height())
            for x in range(image.width())
            if image.pixel(x, y) == accent
        )

    window._distributions_dock.setVisible(False)
    app.processEvents()
    assert accent_pixels() == 0

    window._distributions_dock.setVisible(True)
    app.processEvents()
    assert accent_pixels() > 0

    window._distributions_dock.setVisible(False)
