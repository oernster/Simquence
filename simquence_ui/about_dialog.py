from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from simquence_ui.auto_scroller import attach
from simquence_ui.first_stop_dialog import FirstStopDialog
from simquence_ui.icon_resolver import get_app_icon_path, get_app_icon_png_path
from simquence_ui.pane_focus import follow_overflow

# The badge beside the title. Square, large enough to read as the product's
# mark rather than as decoration.
_BADGE_PX = 96
_DIALOG_MIN_WIDTH = 540


@dataclass(frozen=True)
class AboutDialogContent:
    title: str
    body: str


class AboutDialog(FirstStopDialog):
    def __init__(self, parent: QWidget, *, content: AboutDialogContent) -> None:
        super().__init__(parent)
        # Keep short to avoid truncation on small dialogs / narrow screens.
        self.setWindowTitle("About")

        # About dialogs should not be maximizable (awkward UX for a small,
        # mostly-static content window); they must still be closable.
        #
        # On Windows, using a fixed-size dialog hint is the most reliable way to
        # remove the maximize button while keeping the close button.
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        self.setSizeGripEnabled(False)

        self.setModal(True)
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        title = QLabel(content.title)
        title.setObjectName("about_title")
        title.setTextFormat(Qt.TextFormat.PlainText)
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSizeF(max(10.0, title_font.pointSizeF() + 2.0))
        title.setFont(title_font)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(title)

        # The real generated icon, never a glyph painted from a font: the badge
        # here, the taskbar and the installer all have to be the same mark, which
        # only a file can guarantee.
        badge_path = get_app_icon_png_path(_BADGE_PX)
        if badge_path is not None:
            badge = QLabel()
            badge.setObjectName("about_icon")
            badge.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            )
            badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            badge.setPixmap(
                QPixmap(str(badge_path)).scaled(
                    _BADGE_PX,
                    _BADGE_PX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            header.addWidget(badge)

        icon_path = get_app_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        root.addLayout(header)

        # A browser rather than a label: the credits carry licence names and
        # links; a label can neither scroll them nor open one.
        body = QTextBrowser()
        body.setObjectName("about_body")
        body.setOpenExternalLinks(True)
        body.setHtml(content.body)
        root.addWidget(body, 1)
        # The scroller stays attached: it is free while nothing overflows and
        # it takes over if a theme or font change ever makes the text longer.
        attach(body)
        follow_overflow(body)
        self._body = body

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._fit_height_to_text()
        super().showEvent(event)

    def _fit_height_to_text(self) -> None:
        """Make the dialog tall enough that the whole text shows unscrolled.

        Sized from the document itself, at show time, because nothing earlier
        knows the answer: the stylesheet's `min-height` replaces any minimum
        set at construction when the browser is polished (measured: a minimum
        of 320 became 48, leaving a 192px body over 587px of text). The
        text's height also depends on the width it wraps to. The text is measured
        at the width it has WITH a scrollbar beside it, the narrower and so
        taller case: sized for the exact unscrolled fit instead, a text that
        rewraps taller beside a bar keeps the bar it was meant to lose
        (measured offscreen: 15px left to scroll). The frame, border and
        padding around the text are measured too.
        """

        body = self._body
        text = body.document().clone()
        bar_width = body.verticalScrollBar().sizeHint().width()
        text.setTextWidth(body.contentsRect().width() - bar_width)
        chrome = body.height() - body.viewport().height()
        wanted = math.ceil(text.size().height()) + chrome
        if wanted > body.height():
            self.resize(self.width(), self.height() + wanted - body.height())
