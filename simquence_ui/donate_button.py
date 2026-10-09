"""The donate button, which sits in the top bar immediately left of the theme toggle.

It belongs to nothing else on screen, so it sits beside the one other control
that is about the application rather than the model. As a member of the tray it
is drawn at the tray's own glyph height, not a smaller fraction of it; the mark
is wide, so its icon keeps the render's aspect at that height.

A press hands the address to the desktop. The application never fetches the
page; a desktop that declines says so, because silence leaves a button that
appears to do nothing.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from simquence_ui import links
from simquence_ui.about_text import APP_NAME, DONATE_URL
from simquence_ui.icon_resolver import get_donate_png_path
from simquence_ui.top_bar_buttons import GLYPH_PX, glyph_button

DONATE_BUTTON_NAME = "donate_btn"

# The picture says nothing about leaving the application, so the tooltip does.
DONATE_TOOLTIP = f"Donate to support {APP_NAME} (opens your browser)"

DONATE_REFUSED_TITLE = "Donate"
DONATE_REFUSED_TEXT = (
    f"Could not open a browser for the donation page. The page is at {DONATE_URL}"
)


def open_donation(parent: QWidget) -> None:
    """Hand the donation page to whatever the desktop opens links with."""

    if not links.open_externally(DONATE_URL):
        QMessageBox.information(parent, DONATE_REFUSED_TITLE, DONATE_REFUSED_TEXT)


def _donate_icon() -> tuple[QIcon, QSize]:
    """The mark and the size to draw it at; an empty icon when it is absent."""

    path = get_donate_png_path()
    if path is None:
        return QIcon(), QSize(GLYPH_PX, GLYPH_PX)
    pixmap = QPixmap(str(path))
    width = round(pixmap.width() * GLYPH_PX / pixmap.height())
    return QIcon(pixmap), QSize(width, GLYPH_PX)


def build_donate_button(parent: QWidget) -> QPushButton:
    """The donate button, its press reporting a refusal against `parent`."""

    icon, size = _donate_icon()
    button = glyph_button(
        icon,
        tooltip=DONATE_TOOLTIP,
        on_clicked=lambda: open_donation(parent),
        icon_size=size,
    )
    button.setObjectName(DONATE_BUTTON_NAME)
    button.setAccessibleName(DONATE_TOOLTIP)
    return button
