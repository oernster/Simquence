"""The Guide's toolbar section: every control, led by the picture it wears.

An icon guide showing something other than the icon is worse than no guide, so
each line carries the same file the toolbar draws, resolved when the Guide
opens. A picture that cannot be found leaves its line without one rather than
stopping the Guide from opening.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from simquence_ui.icon_resolver import (
    BOOK_ART,
    COMPOSE_ART,
    DISTRIBUTIONS_ART,
    DONATE_PNG_NAME,
    INFO_ART,
    OPEN_EDIT_ART,
    SAVE_EXPORT_ART,
    get_asset_path,
)
from simquence_ui.theme_toggle import MOON, SUN

# Height of a picture in the text. Large enough that the pictures' detail
# survives, small enough to sit on a line of reading text.
INLINE_ICON_PX = 32

# Left to right, as the bar draws them: the picture, the name, what it does.
TOOLBAR_LINES: tuple[tuple[str, str, str], ...] = (
    (
        SAVE_EXPORT_ART,
        "Export runs",
        "save the last run's results as a zip of plain text. Available once "
        "something has run.",
    ),
    (
        BOOK_ART,
        "How to Read",
        "what the histogram, the percentiles and the critical paths mean.",
    ),
    (COMPOSE_ART, "Compose", "write a new model in four parts, with no JSON."),
    (
        OPEN_EDIT_ART,
        "Edit",
        "change the loaded model in the same composer. Available once a model "
        "is open.",
    ),
    (
        DISTRIBUTIONS_ART,
        "Distributions",
        "in the middle of the bar: open or close the histogram and the "
        "critical-path frequency chart. Available once something has run; "
        "while the panel is open the button is yellow.",
    ),
    (
        DONATE_PNG_NAME,
        "Donate",
        "opens the donation page in your browser. Simquence itself sends nothing.",
    ),
)

_THEME_LINE = (
    "switch between the light and dark themes. It shows the one it will switch TO."
)
_GUIDE_LINE = "this Guide."


def _img(path: Path | None, px: int, *, square: bool = True) -> str:
    """One picture as inline HTML, centred on the line; empty when absent."""

    if path is None:
        return ""
    width = f'width="{px}" ' if square else ""
    return (
        f'<img src="file:///{path.as_posix()}" {width}height="{px}" '
        'style="vertical-align: middle"> '
    )


def toolbar_html(
    path_of: Callable[[str], Path | None] = get_asset_path,
    px: int = INLINE_ICON_PX,
) -> str:
    """The section, with each picture resolved through `path_of`."""

    rows = [
        f"<p>{_img(path_of(art), px, square=art != DONATE_PNG_NAME)}"
        f"<b>{name}</b>: {text}</p>"
        for art, name, text in TOOLBAR_LINES
    ]
    rows.append(f"<p>{SUN} / {MOON} <b>Light and dark</b>: {_THEME_LINE}</p>")
    rows.append(f"<p>{_img(path_of(INFO_ART), px)}<b>Guide</b>: {_GUIDE_LINE}</p>")
    return (
        "<h3>The toolbar, left to right</h3>\n"
        + "\n".join(rows)
        + "\n<p>Hover any button to see its name.</p>\n"
    )
