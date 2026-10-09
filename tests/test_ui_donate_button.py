"""The donate button: where it sits, what it asks for and what a refusal says.

The links seam is replaced in every test that presses the button, so the suite
never opens a real browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from simquence_ui import donate_button, icon_resolver, links
from simquence_ui.about_text import DONATE_URL
from simquence_ui.icon_resolver import DONATE_PNG_NAME, get_donate_png_path
from simquence_ui.main_window_top_bar import TopBar, build_top_bar
from simquence_ui.top_bar_buttons import GLYPH_PX

# Written out in full rather than read back from the constant, so a typo in the
# payment address fails here instead of sending a supporter to the wrong page.
SIMQUENCE_DONATE_URL = "https://www.paypal.com/ncp/payment/Y275VZ7R2NUNW"


def _ignore(*_args: object) -> None:
    return None


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def bar(app: QApplication) -> tuple[QWidget, TopBar]:
    parent = QWidget()
    top_bar = build_top_bar(
        parent,
        on_save_log_clicked=_ignore,
        on_show_distributions_clicked=_ignore,
        on_show_guide_clicked=_ignore,
        on_show_how_to_read_clicked=_ignore,
        on_toggle_model_composer_clicked=_ignore,
        on_edit_model_clicked=_ignore,
        on_theme_changed=_ignore,
    )
    yield parent, top_bar
    parent.deleteLater()


def test_the_button_sits_immediately_left_of_the_theme_toggle(
    bar: tuple[QWidget, TopBar],
) -> None:
    _, top_bar = bar
    row = top_bar.theme_toggle.parentWidget().layout()
    donate_at = row.indexOf(top_bar.donate_btn)
    assert donate_at >= 0
    assert row.indexOf(top_bar.theme_toggle) == donate_at + 1

    stops = top_bar.widget.ring_stops()
    assert stops.index(top_bar.theme_toggle) == stops.index(top_bar.donate_btn) + 1


def test_the_button_is_enabled_and_says_the_browser_opens(
    bar: tuple[QWidget, TopBar],
) -> None:
    _, top_bar = bar
    assert top_bar.donate_btn.isEnabled()
    assert "opens your browser" in top_bar.donate_btn.toolTip()


def test_a_press_asks_the_desktop_for_the_one_address(
    bar: tuple[QWidget, TopBar], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, top_bar = bar
    asked: list[str] = []

    def fake_open(address: str) -> bool:
        asked.append(address)
        return True

    monkeypatch.setattr(links, "open_externally", fake_open)
    top_bar.donate_btn.click()
    assert asked == [SIMQUENCE_DONATE_URL]


def test_the_seam_hands_the_address_to_the_desktop(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only the desktop's opener is replaced, so the seam's own line runs while
    # no browser opens; the desktop's answer comes back unchanged.
    handed: list[str] = []

    def fake_open_url(url: QUrl) -> bool:
        handed.append(url.toString())
        return False

    monkeypatch.setattr(QDesktopServices, "openUrl", fake_open_url)
    assert links.open_externally(SIMQUENCE_DONATE_URL) is False
    assert handed == [SIMQUENCE_DONATE_URL]


def test_the_address_is_simquences_own_and_secure() -> None:
    assert DONATE_URL == SIMQUENCE_DONATE_URL
    assert DONATE_URL.startswith("https://")


def test_a_desktop_that_refuses_is_reported(
    bar: tuple[QWidget, TopBar], monkeypatch: pytest.MonkeyPatch
) -> None:
    parent, top_bar = bar
    told: list[tuple[QWidget, str, str]] = []
    monkeypatch.setattr(links, "open_externally", lambda _address: False)
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda where, title, text: told.append((where, title, text)),
    )
    top_bar.donate_btn.click()
    assert told == [
        (parent, donate_button.DONATE_REFUSED_TITLE, donate_button.DONATE_REFUSED_TEXT)
    ]
    assert DONATE_URL in told[0][2]


def test_the_mark_is_drawn_at_the_trays_glyph_height(
    bar: tuple[QWidget, TopBar],
) -> None:
    if get_donate_png_path() is None:
        pytest.skip("generate_icons.py has not been run in this checkout")
    _, top_bar = bar
    size = top_bar.donate_btn.iconSize()
    assert size.height() == GLYPH_PX
    assert size.width() > GLYPH_PX  # the mark is wide, so its aspect is kept


def test_a_missing_mark_still_builds_a_button(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(donate_button, "get_donate_png_path", lambda: None)
    parent = QWidget()
    button = donate_button.build_donate_button(parent)
    assert button.icon().isNull()
    assert button.iconSize().height() == GLYPH_PX
    parent.deleteLater()


def test_the_resolver_finds_the_mark_only_where_it_exists(tmp_path: Path) -> None:
    assert get_donate_png_path(tmp_path) is None
    (tmp_path / DONATE_PNG_NAME).write_bytes(b"")
    assert get_donate_png_path(tmp_path) == tmp_path / DONATE_PNG_NAME


def test_the_resolver_answers_none_without_an_assets_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(icon_resolver, "find_assets_dir", lambda: None)
    assert get_donate_png_path() is None
