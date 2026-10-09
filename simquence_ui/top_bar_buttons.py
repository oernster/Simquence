"""The buttons the top bar is built from, separate from the bar that orders them.

`main_window_top_bar` decides what sits where and in what order the ring reads
them; this module decides what one button looks like. Kept apart so the bar
stays a layout and each kind of button has one place that says how it is made.

Every action wears a supplied picture from `assets/` rather than an emoji or a
drawn glyph: an emoji is whatever font happens to be installed, so the same bar
looked different on every machine.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from simquence_ui.icon_resolver import DISTRIBUTIONS_ART, get_asset_path
from simquence_ui.toolbar_metrics import ARTWORK_PX, GLYPH_PX, TOOLBAR_BUTTON_PX

# How much of the supplied picture is kept before Qt scales it to the button:
# four times the drawn size, so it stays sharp under display scaling without
# holding a full-size picture for every state.
_ARTWORK_WORK_PX = ARTWORK_PX * 4

# A disabled picture is grey and faint. Keeping any of its colour would read as
# half-available, which is not a state this application has.
DISABLED_OPACITY = 0.45

# Named so the stylesheet can say what CHECKED looks like on it. The name is
# shared with the sheet rather than written out twice.
DISTRIBUTIONS_BUTTON_NAME = "distributions_btn"

# The distributions toggle sits dead centre. A minimum width holds the centre
# steady if its picture is ever missing, since a control that collapses would
# move the thing it is supposed to centre.
TOP_BADGE_PX = TOOLBAR_BUTTON_PX


def _trimmed(source: QPixmap) -> QPixmap:
    """The picture without its transparent margin, so every action fills the
    same box whatever margin its artwork was drawn with."""

    bounds = QRegion(source.mask()).boundingRect()
    return source.copy(bounds) if not bounds.isEmpty() else source


def _greyed(source: QPixmap) -> QPixmap:
    """The picture in grey alone, faded, keeping its outline."""

    grey = QPixmap.fromImage(
        source.toImage()
        .convertToFormat(QImage.Format.Format_ARGB32)
        .convertToFormat(QImage.Format.Format_Grayscale8)
    )
    masked = QPixmap(source.size())
    masked.fill(Qt.GlobalColor.transparent)
    painter = QPainter(masked)
    painter.drawPixmap(0, 0, grey)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawPixmap(0, 0, source)
    painter.end()

    out = QPixmap(source.size())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setOpacity(DISABLED_OPACITY)
    painter.drawPixmap(0, 0, masked)
    painter.end()
    return out


def artwork_icon(path: Path | None) -> QIcon:
    """A toolbar icon from a supplied picture; empty when there is none.

    A checked button keeps the picture as drawn and says "on" with its fill.
    Flattening the picture to one ink for that state was measured: the
    distributions chart became a dark mound that no longer read as a chart,
    while in full colour its outline keeps it legible on the yellow fill.
    """

    if path is None:
        return QIcon()
    source = QPixmap(str(path))
    if source.isNull():
        return QIcon()
    art = _trimmed(source).scaled(
        _ARTWORK_WORK_PX,
        _ARTWORK_WORK_PX,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    disabled = _greyed(art)
    icon = QIcon()
    icon.addPixmap(art, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(disabled, QIcon.Mode.Disabled, QIcon.State.Off)
    return icon


def build_centre_mark(
    parent: QWidget, *, tooltip: str, on_clicked: Callable[[], None]
) -> QPushButton:
    """The distributions toggle, dead centre.

    The panel it opens is the point of running anything, so it takes the most
    prominent place on the bar rather than competing from one end.

    The height is fixed and the WIDTH is left natural. Fixing both to a size
    smaller than the frame the stylesheet computes makes Qt lay the frame out at
    its natural size and clip it at the widget edge, which slices the bottom
    border off and leaves a ring that stops short.
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
    _wear(
        mark, artwork_icon(get_asset_path(DISTRIBUTIONS_ART)), fallback="Distributions"
    )
    return mark


def _wear(button: QPushButton, icon: QIcon, *, fallback: str) -> None:
    """Put the picture on; a missing picture leaves words rather than a blank."""

    if icon.isNull():
        button.setText(fallback)
        return
    button.setIcon(icon)
    button.setIconSize(QSize(ARTWORK_PX, ARTWORK_PX))


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


def artwork_button(
    art_name: str,
    *,
    fallback: str,
    tooltip: str,
    on_clicked: Callable[[], None],
) -> QPushButton:
    """A toolbar button wearing one of the supplied pictures from `assets/`."""

    button = QPushButton()
    button.setToolTip(tooltip)
    button.setProperty("role", "icon-action")
    button.setFixedHeight(TOOLBAR_BUTTON_PX)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    button.clicked.connect(on_clicked)
    _wear(button, artwork_icon(get_asset_path(art_name)), fallback=fallback)
    return button
