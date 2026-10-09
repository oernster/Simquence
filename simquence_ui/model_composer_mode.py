from __future__ import annotations

"""Which model the composer is holding: a new one, else the one that was opened.

Compose and Edit reach the same composer, which is right: there is one way to
author a model. What was wrong is that they reached it in the same STATE. The
composer is built once and keeps what it last held, so after Edit, Compose
reopened the loaded model rather than starting a new one; nothing on screen
said which of the two it was.

The rules (ruled by Oliver, 2026-10-09):

- Compose opens a blank new model, unless the composer holds an unfinished new
  model of the user's own, which it reopens. Edit's loaded model never carries
  over into Compose.
- Edit fills the composer with the loaded model; where that would replace an
  unfinished new model, it asks first.
- The title and the title-bar icon name the mode: the Compose picture with
  "new model"; the Open/Edit picture and "editing <name>".
"""

from PySide6.QtGui import QIcon

from simquence_ui.icon_resolver import COMPOSE_ART, OPEN_EDIT_ART, get_asset_path
from simquence_ui.model_composer_load import load_raw_model
from simquence_ui.model_composer_types import ComposerState, build_raw_model_dict

TITLE = "Model Composer"
NEW_MODEL_TITLE = f"{TITLE}: new model"


def editing_title(model_name: str) -> str:
    return f"{TITLE}: editing {model_name}"


def show_mode(dialog, *, editing: str | None) -> None:
    """Name the mode in the title and wear the matching picture.

    A missing picture leaves the application's icon in place rather than a
    blank corner; the title still says which mode this is.
    """

    title = NEW_MODEL_TITLE if editing is None else editing_title(editing)
    dialog.setWindowTitle(title)
    art = get_asset_path(COMPOSE_ART if editing is None else OPEN_EDIT_ART)
    if art is not None:
        dialog.setWindowIcon(QIcon(str(art)))


def _snapshot(dialog) -> tuple[str, dict]:
    dialog.sync_from_ui()
    state: ComposerState = dialog.state
    return state.model_name, build_raw_model_dict(state)


def remember_fresh_model(dialog) -> None:
    """Record what a freshly built composer holds, then name the mode.

    That, not `ComposerState()`, is a blank model: the editors add defaults of
    their own as they are built (measured: the contexts editor starts with a
    `ui` context), so a composer nobody has touched differs from the bare
    state. Called once, at the end of construction.
    """

    dialog._fresh_model = _snapshot(dialog)  # noqa: SLF001
    show_mode(dialog, editing=None)


def holds_own_work(dialog) -> bool:
    """Whether the composer holds a new model the user has started on.

    A view of an opened model is not the user's own work: the file is on disk.
    A new model is theirs once it differs from a fresh one in any way.
    """

    if dialog.is_showing_loaded_model():
        return False
    return _snapshot(dialog) != dialog._fresh_model  # noqa: SLF001


def start_new_model(dialog) -> None:
    """Put the editors back to a fresh new model and say so."""

    name, raw = dialog._fresh_model  # noqa: SLF001
    load_raw_model(dialog, raw, model_name=name)
    dialog._showing_loaded_model = False  # noqa: SLF001
    dialog._refresh_task_rows()  # noqa: SLF001
    show_mode(dialog, editing=None)
