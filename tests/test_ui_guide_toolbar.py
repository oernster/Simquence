"""The Guide's toolbar section names every control, led by its real picture."""

from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication, QTextBrowser, QWidget

from simquence_ui.guide_dialog import GuideDialog
from simquence_ui.guide_toolbar import TOOLBAR_LINES, toolbar_html
from simquence_ui.icon_resolver import get_asset_path


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


# The bar's own order, left to right, by the name each line gives it.
BAR_ORDER = (
    "Export runs",
    "How to Read",
    "Compose",
    "Edit",
    "Distributions",
    "Donate",
    "Light and dark",
    "Guide",
)


def test_every_control_is_named_in_the_order_the_bar_draws_them() -> None:
    html = toolbar_html()
    positions = [html.index(f"<b>{name}</b>") for name in BAR_ORDER]
    assert positions == sorted(positions)


def test_every_pictured_line_carries_the_file_the_toolbar_draws() -> None:
    html = toolbar_html()
    for art, _name, _text in TOOLBAR_LINES:
        path = get_asset_path(art)
        assert path is not None, art
        assert path.as_posix() in html, art


def test_a_missing_picture_leaves_the_words() -> None:
    def nothing(_name: str) -> Path | None:
        return None

    html = toolbar_html(path_of=nothing)
    assert "<img" not in html
    for name in BAR_ORDER:
        assert f"<b>{name}</b>" in html


def test_the_open_guide_carries_the_section(app: QApplication) -> None:
    holder = QWidget()
    dialog = GuideDialog(holder)
    text = dialog.findChild(QTextBrowser).toPlainText()
    assert "The toolbar, left to right" in text
    assert text.index("The toolbar, left to right") < text.index(
        "Run something, in six steps"
    )
    holder.deleteLater()
