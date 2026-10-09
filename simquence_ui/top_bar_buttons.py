"""The buttons the top bar is built from, separate from the bar that orders them.

`main_window_top_bar` decides what sits where and in what order the ring reads
them; this module decides what one button looks like. Kept apart so the bar
stays a layout and each kind of button has one place that says how it is made.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from simquence_ui.glyphs import two_tone_icon
from simquence_ui.icon_resolver import get_app_icon_png_path
from simquence_ui.theme import Theme, tokens_for

TOOLBAR_BUTTON_PX = 34

# The glyph inside a toolbar button, leaving room for the 2px ring and the
# button's own padding without crowding either.
GLYPH_PX = 20

# Named so the stylesheet can say what CHECKED looks like on it. The name is
# shared with the sheet rather than written out twice.
DISTRIBUTIONS_BUTTON_NAME = "distributions_btn"

# The application mark, in the middle of the bar. Painted from the generated
# icon set rather than an emoji glyph, so the mark in the bar, the mark in the
# taskbar, the mark on the shortcut and the mark in About are all one file.
TOP_BADGE_PX = 36

# The mark is the centrepiece, so it is drawn a little larger than the glyphs
# flanking it, while still fitting inside a button of the tray's own height.
CENTRE_MARK_PX = 24

# Ask for a larger source and scale it down: downscaling a slightly-too-big icon
# looks better than upscaling a slightly-too-small one.
_MARK_SOURCE_PX = 64


def build_centre_mark(
    parent: QWidget, *, tooltip: str, on_clicked: Callable[[], None]
) -> QPushButton:
    """The application mark, dead centre, doubling as the distributions toggle.

    It was decoration and is now the control, which is the same widget doing a
    job instead of sitting there: the mark is the most prominent thing on the
    bar and the panel it opens is the point of running anything, so the two
    belong together rather than competing for attention from opposite ends.

    The height is fixed and the WIDTH is left natural. Fixing both to a size
    smaller than the frame the stylesheet computes makes Qt lay the frame out at
    its natural size and clip it at the widget edge, which slices the bottom
    border off and leaves a ring that stops short. A minimum width holds the
    centre steady if the icon set is ever missing, since a mark that collapses
    would move the thing it is supposed to centre.
    """

    mark = QPushButton(parent)
    mark.setObjectName(DISTRIBUTIONS_BUTTON_NAME)
    mark.setProperty("role", "icon-action")
    mark.setFixedHeight(TOOLBAR_BUTTON_PX)
    mark.setMinimumWidth(TOP_BADGE_PX)
    mark.setToolTip(tooltip)
    mark.setCheckable(True)
    mark.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    mark.clicked.connect(on_clicked)

    mark_path = get_app_icon_png_path(_MARK_SOURCE_PX)
    if mark_path is not None:
        mark.setIcon(_mark_icon(QPixmap(str(mark_path))))
        mark.setIconSize(QSize(CENTRE_MARK_PX, CENTRE_MARK_PX))
    return mark


def _mark_icon(source: QPixmap) -> QIcon:
    """The mark, plus a second rendering of it for the checked state.

    The mark's hands and hub are banana and the checked fill is banana, so on
    its own the mark loses them at exactly the moment the button is saying
    something. Measured at the 24px the bar draws, the same 74% of the mark
    clears both fills by luminance; it is not the same 74%: on the blue fill the
    quarter that does not clear is the case, which is warm against a cool fill
    and so is separated by hue instead, while on the banana fill it is the
    hands, which are that same yellow and therefore genuinely gone. A
    stylesheet cannot reach inside an icon, so the second rendering is the same
    answer the drawn glyphs already use, in the same ink.
    """

    icon = QIcon()
    icon.addPixmap(source, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(
        _inked(source, tokens_for(Theme.DARK).accent_text),
        QIcon.Mode.Normal,
        QIcon.State.On,
    )
    return icon


def _inked(source: QPixmap, colour: str) -> QPixmap:
    """The same shape in one flat colour, keeping its alpha.

    The mark is strokes rather than a solid body, so flattening it reads as the
    same stopwatch drawn in a different ink rather than as a blob of its
    outline.
    """

    out = QPixmap(source.size())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(out.rect(), QColor(colour))
    painter.end()
    return out


def icon_button(
    glyph: str, *, tooltip: str, on_clicked: Callable[[], None]
) -> QPushButton:
    """A toolbar button captioned with an emoji glyph."""

    button = QPushButton(glyph)
    button.setToolTip(tooltip)
    button.setProperty("role", "icon-action")
    button.setFixedHeight(TOOLBAR_BUTTON_PX)
    button.clicked.connect(on_clicked)
    return button


def glyph_button(
    icon: QIcon,
    *,
    tooltip: str,
    on_clicked: Callable[[], None],
    icon_size: QSize | None = None,
) -> QPushButton:
    """A toolbar button carrying an already-drawn icon; square unless sized."""

    button = QPushButton()
    button.setIcon(icon)
    button.setIconSize(icon_size or QSize(GLYPH_PX, GLYPH_PX))
    button.setToolTip(tooltip)
    button.setProperty("role", "icon-action")
    button.setFixedHeight(TOOLBAR_BUTTON_PX)
    button.clicked.connect(on_clicked)
    return button


def drawn_icon_button(
    body_of: Callable[..., str],
    *,
    tooltip: str,
    on_clicked: Callable[[], None],
    checkable: bool = False,
) -> QPushButton:
    """A toolbar button carrying a drawn two-tone glyph rather than an emoji.

    The colours come from the dark theme's tokens because the button fill is
    the same blue in both themes, so one rendering serves both and the glyph
    never has to be redrawn on a theme switch.
    """

    tokens = tokens_for(Theme.DARK)
    return glyph_button(
        two_tone_icon(
            body_of,
            ink=tokens.primary_text,
            accent=tokens.accent,
            disabled=tokens.muted_text,
            # A checked button's fill is the light accent, so its glyph takes
            # the accent's dark ink. Without it the icon stays near-white and
            # vanishes at the moment the button is saying something.
            checked_ink=tokens.accent_text if checkable else None,
            size=GLYPH_PX,
        ),
        tooltip=tooltip,
        on_clicked=on_clicked,
    )
