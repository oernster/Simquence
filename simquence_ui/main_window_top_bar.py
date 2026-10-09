from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from simquence_ui import main_window_actions as actions
from simquence_ui.donate_button import build_donate_button
from simquence_ui.guide_text import GUIDE_TITLE
from simquence_ui.icon_resolver import (
    COMPOSE_ART,
    GUIDE_ART,
    OPEN_EDIT_ART,
    OUTPUT_INFO_ART,
    SAVE_EXPORT_ART,
)
from simquence_ui.theme import Theme
from simquence_ui.theme_toggle import ThemeToggle
from simquence_ui.top_bar_buttons import artwork_button, build_centre_mark

# The tray is a band of its own rather than controls floating on the window.
# The stylesheet gives it a surface and a bottom edge; it needs a name to be
# addressed by, plus vertical padding so the band reads as a band.
TRAY_OBJECT_NAME = "top_tray"
TRAY_PAD_Y = 6

MARGIN_SIDE = 10
BUTTON_SPACING = 8


class NavBand(QWidget):
    """The tray, which knows the order its own controls are READ in.

    The mark is an overlay sharing one grid cell with the row of buttons,
    because centring on the BAR cannot be done with a row of stretches. Layout
    order therefore reaches every button first and the mark last, so the ring
    stepped from the leftmost button all the way to the theme toggle at the far
    right and only THEN back to the mark in the middle. The one control on the
    bar nobody can miss with their eye was the last one the keyboard offered,
    which is indistinguishable from the ring having skipped it.

    A container whose layout is deliberately not in reading order has to state
    the reading order itself rather than leave it to be inferred.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._ring_stops: tuple[QWidget, ...] = ()

    def set_ring_stops(self, stops: tuple[QWidget, ...]) -> None:
        self._ring_stops = stops

    def ring_stops(self) -> tuple[QWidget, ...]:
        """Left to right as drawn, which is not the order the layout holds."""

        return self._ring_stops


@dataclass(frozen=True, slots=True)
class TopBar:
    """The top bar and every control on it the window needs to reach later."""

    widget: NavBand
    save_log_btn: QPushButton
    distributions_btn: QPushButton
    guide_btn: QPushButton
    how_to_read_btn: QPushButton
    compose_btn: QPushButton
    edit_btn: QPushButton
    donate_btn: QPushButton
    theme_toggle: ThemeToggle


def build_top_bar(
    parent: QWidget,
    *,
    on_save_log_clicked: Callable[[], None],
    on_show_distributions_clicked: Callable[[], None],
    on_show_guide_clicked: Callable[[], None],
    on_show_how_to_read_clicked: Callable[[], None],
    on_toggle_model_composer_clicked: Callable[[], None],
    on_edit_model_clicked: Callable[[], None],
    on_theme_changed: Callable[[Theme], None],
) -> TopBar:
    """Build the top bar: actions at the edges, the distributions toggle dead
    centre (called the mark below).

    The mark is centred on the BAR, which a row of stretches cannot do. Three
    stretches centre it in the space LEFT OVER between the flanking groups;
    those groups are nowhere near the same width, so it lands well right of
    centre (134px out of 1400, measured). Equalising two grid columns by stretch
    does not work either, because a column never shrinks below its own content.

    What does work is an overlay: the controls and the mark occupy the SAME grid
    cell, that cell is the whole bar, then the mark centres itself in it. The
    mark is added second, so it is the one that takes a click where they meet.
    """

    top_bar = NavBand(parent)
    top_bar.setObjectName(TRAY_OBJECT_NAME)
    grid = QGridLayout(top_bar)
    grid.setContentsMargins(MARGIN_SIDE, TRAY_PAD_Y, MARGIN_SIDE, TRAY_PAD_Y)

    controls = QWidget(top_bar)
    layout = QHBoxLayout(controls)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(BUTTON_SPACING)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    save_log_btn = artwork_button(
        SAVE_EXPORT_ART,
        fallback="Export",
        tooltip="Export runs as zip…",
        on_clicked=on_save_log_clicked,
    )
    save_log_btn.setObjectName("save_log_btn")
    layout.addWidget(save_log_btn, 0, Qt.AlignmentFlag.AlignTop)

    # Immediately left of the info button, because the pair is one idea in two
    # halves: this one says which button to press, that one says what the
    # output means.
    guide_btn = artwork_button(
        GUIDE_ART,
        fallback="Guide",
        tooltip=GUIDE_TITLE,
        on_clicked=on_show_guide_clicked,
    )
    guide_btn.setObjectName("guide_btn")
    layout.addWidget(guide_btn, 0, Qt.AlignmentFlag.AlignTop)

    how_to_read_btn = artwork_button(
        OUTPUT_INFO_ART,
        fallback="How to Read",
        tooltip="How to Read Simquence Output",
        on_clicked=on_show_how_to_read_clicked,
    )
    how_to_read_btn.setObjectName("how_to_read_btn")
    layout.addWidget(how_to_read_btn, 0, Qt.AlignmentFlag.AlignTop)

    # Not checkable. The composer is a modal dialog: while it is open it IS the
    # window; a button reporting that from underneath it says nothing.
    compose_btn = artwork_button(
        COMPOSE_ART,
        fallback="Compose",
        tooltip=actions.COMPOSE_READY,
        on_clicked=on_toggle_model_composer_clicked,
    )
    compose_btn.setObjectName("compose_model_btn")
    layout.addWidget(compose_btn, 0, Qt.AlignmentFlag.AlignTop)

    edit_btn = artwork_button(
        OPEN_EDIT_ART,
        fallback="Edit",
        tooltip=actions.EDIT_NEEDS_MODEL,
        on_clicked=on_edit_model_clicked,
    )
    edit_btn.setObjectName("edit_model_btn")
    layout.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignTop)

    layout.addStretch(1)

    # Immediately left of the theme toggle: the two are the only controls about
    # the application rather than the model, so they sit together at the edge.
    donate_btn = build_donate_button(parent)
    layout.addWidget(donate_btn, 0, Qt.AlignmentFlag.AlignTop)

    theme_toggle = ThemeToggle(default=Theme.DARK, parent=parent)
    theme_toggle.theme_changed.connect(on_theme_changed)
    layout.addWidget(theme_toggle, 0, Qt.AlignmentFlag.AlignTop)

    distributions_btn = build_centre_mark(
        top_bar,
        tooltip=actions.DISTRIBUTIONS_NEEDS_OUTPUTS,
        on_clicked=on_show_distributions_clicked,
    )

    grid.addWidget(controls, 0, 0)
    grid.addWidget(
        distributions_btn,
        0,
        0,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
    )

    # Left to right as the bar is drawn: the action group, then the mark in the
    # middle, then the donate button and the theme toggle on the far right.
    # Stated here because this is the one place every control is in hand at
    # once. It is asserted against the band's real children by a test, so adding
    # a button and forgetting this line fails the suite rather than quietly
    # dropping it off the ring.
    top_bar.set_ring_stops(
        (
            save_log_btn,
            guide_btn,
            how_to_read_btn,
            compose_btn,
            edit_btn,
            distributions_btn,
            donate_btn,
            theme_toggle,
        )
    )

    return TopBar(
        widget=top_bar,
        save_log_btn=save_log_btn,
        distributions_btn=distributions_btn,
        guide_btn=guide_btn,
        how_to_read_btn=how_to_read_btn,
        compose_btn=compose_btn,
        edit_btn=edit_btn,
        donate_btn=donate_btn,
        theme_toggle=theme_toggle,
    )
