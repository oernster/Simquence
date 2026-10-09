"""The top bar's pictures: every action wears one; each wears it honestly.

The rules come from the glyphs these pictures replaced and still hold: a
disabled control shows none of its colour, so it never reads as half-available;
a missing picture leaves words rather than a blank button nobody can identify.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QImage, QRegion
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from simquence_ui import icon_resolver
from simquence_ui.main_window_top_bar import TopBar, build_top_bar
from simquence_ui.top_bar_buttons import ARTWORK_PX, artwork_button, artwork_icon

# Grey means the three channels agree. Scaling blends neighbours, so a pixel
# that came from grey can still drift by a little.
GREY_TOLERANCE = 8

# Large enough that scaling leaves solid interior pixels to judge colour by.
PROBE_PX = 64

# Scaling can fade the outermost row of a picture to nothing.
EDGE_SLACK_PX = 1

ARTWORK = (
    icon_resolver.SAVE_EXPORT_ART,
    icon_resolver.GUIDE_ART,
    icon_resolver.OUTPUT_INFO_ART,
    icon_resolver.COMPOSE_ART,
    icon_resolver.OPEN_EDIT_ART,
    icon_resolver.DISTRIBUTIONS_ART,
)


def _noop(*_args) -> None:
    return None


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def bar(app: QApplication) -> Iterator[TopBar]:
    holder = QWidget()
    built = build_top_bar(
        holder,
        on_save_log_clicked=_noop,
        on_show_distributions_clicked=_noop,
        on_show_guide_clicked=_noop,
        on_show_how_to_read_clicked=_noop,
        on_toggle_model_composer_clicked=_noop,
        on_edit_model_clicked=_noop,
        on_theme_changed=_noop,
    )
    yield built
    holder.deleteLater()


def _actions(bar: TopBar) -> tuple[QPushButton, ...]:
    return (
        bar.save_log_btn,
        bar.guide_btn,
        bar.how_to_read_btn,
        bar.compose_btn,
        bar.edit_btn,
        bar.distributions_btn,
    )


def _opaque(image: QImage):
    for y in range(image.height()):
        for x in range(image.width()):
            colour = image.pixelColor(x, y)
            if colour.alpha() > 0:
                yield colour


def _is_grey(colour: QColor) -> bool:
    channels = (colour.red(), colour.green(), colour.blue())
    return max(channels) - min(channels) <= GREY_TOLERANCE


@pytest.mark.parametrize("name", ARTWORK)
def test_every_picture_ships_in_assets(name: str) -> None:
    assert icon_resolver.get_asset_path(name) is not None


def test_every_action_wears_a_picture_and_no_words(bar: TopBar) -> None:
    for button in _actions(bar):
        assert button.text() == "", button.objectName()
        assert button.icon().isNull() is False, button.objectName()
        assert button.iconSize() == QSize(ARTWORK_PX, ARTWORK_PX)


def test_a_disabled_picture_keeps_none_of_its_colour(bar: TopBar) -> None:
    size = QSize(PROBE_PX, PROBE_PX)
    for button in _actions(bar):
        icon = button.icon()
        normal = icon.pixmap(size, QIcon.Mode.Normal).toImage()
        disabled = icon.pixmap(size, QIcon.Mode.Disabled).toImage()

        # The pictures are colourful, so the check below can actually fail.
        assert not all(_is_grey(c) for c in _opaque(normal)), button.objectName()
        assert all(_is_grey(c) for c in _opaque(disabled)), button.objectName()


def test_the_picture_fills_its_box_whatever_margin_it_was_drawn_with(
    bar: TopBar,
) -> None:
    """The supplied canvases carry different transparent margins; trimmed, each
    reaches the edge of the box on its longer side."""

    size = QSize(PROBE_PX, PROBE_PX)
    for button in _actions(bar):
        # The visible picture, not the pixmap: an untrimmed square canvas is
        # still a square pixmap, with the picture floating inside its margin.
        drawn = QRegion(button.icon().pixmap(size).mask()).boundingRect()
        longest = max(drawn.width(), drawn.height())
        assert longest >= PROBE_PX - EDGE_SLACK_PX, button.objectName()


def test_a_missing_picture_leaves_words_rather_than_a_blank(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An assets directory with none of the pictures in it.
    monkeypatch.setattr(icon_resolver, "find_assets_dir", lambda: tmp_path)

    button = artwork_button(
        icon_resolver.GUIDE_ART, fallback="Guide", tooltip="Guide", on_clicked=_noop
    )

    assert button.text() == "Guide"
    assert button.icon().isNull()


def test_no_path_or_an_unreadable_file_is_an_empty_icon(
    app: QApplication, tmp_path: Path
) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a picture")

    assert artwork_icon(None).isNull()
    assert artwork_icon(broken).isNull()
