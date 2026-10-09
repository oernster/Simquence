from __future__ import annotations

"""Opening the loaded model in the composer; keeping it in step.

Composing and editing are the same surface reached from two ends, so there is
no second composer here: editing is the compose action with the loaded model put
into the editors first. This lives beside the window for the same reason the
panel policies do, which is that the window is at its size limit and this is
one cohesive job with a rule worth stating.
"""

from PySide6.QtWidgets import QMessageBox

from simquence.io import read_model_json
from simquence_ui.main_window_dock_switching import open_model_composer
from simquence_ui.model_composer_mode import holds_own_work, start_new_model

REPLACE_TITLE = "Replace your new model?"


def replace_question(new_name: str, loaded_name: str) -> str:
    return (
        f"The composer holds your unfinished new model '{new_name}'. Editing "
        f"'{loaded_name}' replaces it; export it first to keep it."
    )


def compose_new_model(window) -> None:
    """Open the composer on a new model: the user's own, else a blank one.

    A view of an opened model is emptied first; the file it showed is on disk,
    so nothing is lost. An unfinished new model of the user's own is reopened
    as it was left. See `model_composer_mode` for the rules.
    """

    composer = window._model_composer  # noqa: SLF001
    if composer.is_showing_loaded_model():
        start_new_model(composer)
    open_model_composer(window)


def _may_replace_own_work(window) -> bool:
    composer = window._model_composer  # noqa: SLF001
    if not holds_own_work(composer):
        return True
    answer = QMessageBox.question(
        window,
        REPLACE_TITLE,
        replace_question(
            composer.state.model_name,
            window._loaded_model.path.stem,  # noqa: SLF001
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes


def open_loaded_model_for_editing(window) -> None:
    """Show the composer, filled with the model that is already loaded.

    Silent when nothing is loaded. The control that reaches this is disabled
    and wearing a red ring that says why, so there is nothing left to tell.

    An unfinished new model of the user's own is replaced only once they say
    so; Cancel, the default, leaves it exactly as it was.

    Filling comes first and opening second, so the composer is never on screen
    showing the previous model for the instant it takes to load the new one.
    """

    if window._loaded_model is None:  # noqa: SLF001
        return
    if not _may_replace_own_work(window):
        return
    load_into_composer(window)
    if not window._model_composer.isVisible():  # noqa: SLF001
        open_model_composer(window)


def load_into_composer(window) -> bool:
    """Put the loaded model into the composer; False when there is none.

    Read from disk rather than from the parsed model the window is holding,
    because the composer edits the FILE's shape: the version key it used, the
    listener spellings it chose, the fields the parser filled in defaults for.
    Round-tripping through the parsed form would quietly rewrite the document.
    """

    loaded = window._loaded_model  # noqa: SLF001
    if loaded is None:
        return False

    raw = read_model_json(loaded.path)
    window._model_composer.load_raw_model(  # noqa: SLF001
        raw, model_name=loaded.path.stem
    )
    return True


def refresh_open_editor(window) -> None:
    """Keep an open editor in step with the model that was just opened.

    An editor showing a model is a view of that model; a view that keeps
    displaying the previous one after another file is opened is simply wrong.

    It follows only while it is BOTH open and showing a loaded model. A
    composer holding something typed from scratch is the user's own work;
    replacing that would be data loss rather than a refresh.
    """

    composer = window._model_composer  # noqa: SLF001
    if composer.isVisible() and composer.is_showing_loaded_model():
        load_into_composer(window)
