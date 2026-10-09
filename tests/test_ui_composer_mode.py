"""Compose and Edit reach one composer; never in the same state.

The composer is built once and kept, so Compose used to reopen whatever Edit
had last put there: after Edit, Compose WAS Edit; nothing on screen said
which one it was. The rules, ruled 2026-10-09, are in `model_composer_mode`.
"""

from __future__ import annotations

import pytest

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from simquence_ui import model_composer_mode as mode
from simquence_ui.example_models import find_examples_dir
from simquence_ui.icon_resolver import COMPOSE_ART, OPEN_EDIT_ART, get_asset_path
from simquence_ui.main_window_editing import REPLACE_TITLE

ICON_PX = 32
OWN_NAME = "mine"


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _Controller(QObject):
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
def window(app: QApplication):
    from simquence_ui.main_window import MainWindow

    w = MainWindow(run_controller=_Controller())
    w.show()
    app.processEvents()
    w._load_model(find_examples_dir() / "checkout.json")
    app.processEvents()
    yield w
    w._model_composer.close()
    w.close()


def _same_picture(icon: QIcon, art: str) -> bool:
    expected = QIcon(str(get_asset_path(art))).pixmap(ICON_PX).toImage()
    return icon.pixmap(ICON_PX).toImage() == expected


def _holds(window) -> tuple[str, int]:
    composer = window._model_composer
    composer.sync_from_ui()
    return composer.state.model_name, len(composer.state.tasks)


def _answer(monkeypatch, button) -> list[tuple]:
    asked: list[tuple] = []

    def question(*args, **_kwargs):
        asked.append(args)
        return button

    monkeypatch.setattr(QMessageBox, "question", question)
    return asked


def _type_own_model(window) -> None:
    window._on_toggle_model_composer_clicked()
    window._model_composer._system.set_values(
        model_name=OWN_NAME, version=2, entry_event="start"
    )
    window._model_composer.close()


def test_a_fresh_composer_says_new_model_and_wears_the_compose_picture(
    app: QApplication,
) -> None:
    from simquence_ui.model_composer_dialog import ModelComposerDialog

    host = QWidget()
    composer = ModelComposerDialog(host)
    assert composer.windowTitle() == mode.NEW_MODEL_TITLE
    assert _same_picture(composer.windowIcon(), COMPOSE_ART)
    assert not mode.holds_own_work(composer)


def test_edit_names_the_model_and_wears_the_edit_picture(window) -> None:
    window._on_edit_model_clicked()
    composer = window._model_composer
    assert composer.windowTitle() == mode.editing_title("checkout")
    assert _same_picture(composer.windowIcon(), OPEN_EDIT_ART)
    assert _holds(window)[0] == "checkout"


def test_compose_after_edit_opens_a_new_model_not_the_loaded_one(window) -> None:
    fresh = _holds(window)
    window._on_edit_model_clicked()
    window._model_composer.close()

    window._on_toggle_model_composer_clicked()

    composer = window._model_composer
    assert _holds(window) == fresh
    assert not composer.is_showing_loaded_model()
    assert composer.windowTitle() == mode.NEW_MODEL_TITLE
    assert _same_picture(composer.windowIcon(), COMPOSE_ART)


def test_compose_reopens_a_new_model_of_the_users_own(window) -> None:
    _type_own_model(window)
    window._on_toggle_model_composer_clicked()
    assert _holds(window)[0] == OWN_NAME


def test_edit_asks_before_replacing_own_work_and_cancel_keeps_it(
    window, monkeypatch
) -> None:
    _type_own_model(window)
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    window._on_edit_model_clicked()

    assert len(asked) == 1
    _parent, title, text, *_ = asked[0]
    assert title == REPLACE_TITLE
    assert OWN_NAME in text and "checkout" in text
    assert _holds(window)[0] == OWN_NAME
    assert not window._model_composer.isVisible()


def test_edit_replaces_own_work_once_told_to(window, monkeypatch) -> None:
    _type_own_model(window)
    _answer(monkeypatch, QMessageBox.StandardButton.Yes)

    window._on_edit_model_clicked()

    assert _holds(window)[0] == "checkout"
    assert window._model_composer.isVisible()


def test_edit_over_an_untouched_composer_asks_nothing(window, monkeypatch) -> None:
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window._on_edit_model_clicked()
    assert asked == []
    assert _holds(window)[0] == "checkout"


def test_edit_with_nothing_loaded_does_nothing(window, monkeypatch) -> None:
    window._loaded_model = None
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window._on_edit_model_clicked()
    assert asked == []
    assert not window._model_composer.isVisible()


def test_loading_into_the_composer_with_nothing_loaded_reports_false(window) -> None:
    from simquence_ui.main_window_editing import load_into_composer

    window._loaded_model = None
    assert load_into_composer(window) is False


def test_a_missing_picture_keeps_the_icon_and_still_names_the_mode(
    app: QApplication, monkeypatch
) -> None:
    from simquence_ui.model_composer_dialog import ModelComposerDialog

    host = QWidget()
    composer = ModelComposerDialog(host)
    before = composer.windowIcon().pixmap(ICON_PX).toImage()
    monkeypatch.setattr(mode, "get_asset_path", lambda _name: None)

    mode.show_mode(composer, editing="x")

    assert composer.windowTitle() == mode.editing_title("x")
    assert composer.windowIcon().pixmap(ICON_PX).toImage() == before
