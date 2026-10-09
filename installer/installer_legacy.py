"""An install left behind under the name the product used to carry.

Simquence was called LatencyLab up to and including 3.3.2. That setup program
installed to its own folder and registered itself under its own name, so
installing Simquence would otherwise leave it standing beside the new one: two
programs, two entries in Apps and two sets of shortcuts.

Nothing here touches the machine. installer_ops reads what is there into a
`LegacyReading`; this module decides from it what may go; installer_ops removes
it. The rule throughout is that only what can be shown to be the old install's
own is removed:

- the folder only when it is named for the old product and holds its program;
- a shortcut only when its target points inside that folder;
- the Apps entry only with the folder; also once the folder it names is gone.

Anything that cannot be shown is reported and left alone, so the user is told
where it is rather than finding it later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import installer_logic as logic

LEGACY_APP_NAME = "LatencyLab"
LEGACY_EXE_NAME = f"{LEGACY_APP_NAME}.exe"
LEGACY_UNINSTALL_KEY = logic.uninstall_key(LEGACY_APP_NAME)


@dataclass(frozen=True, slots=True)
class LegacyShortcut:
    """A shortcut carrying the old name; `target` is None when it was unreadable."""

    link: Path
    target: Path | None


@dataclass(frozen=True, slots=True)
class LegacyReading:
    """What the machine holds under the old name, read once.

    `location` is the registered folder, else the folder the old setup program
    always used when that exists; `exists` and `holds_exe` are facts about it.
    """

    registered: bool
    version: str | None
    location: Path | None
    exists: bool
    holds_exe: bool
    shortcuts: tuple[LegacyShortcut, ...]


@dataclass(frozen=True, slots=True)
class LegacyPlan:
    """What will be removed; also what was found but will be left alone."""

    version: str | None
    folder: Path | None
    registration: bool
    shortcuts: tuple[Path, ...]
    left_alone: tuple[str, ...]

    @property
    def removes_anything(self) -> bool:
        return self.folder is not None or self.registration or bool(self.shortcuts)


def _parts(path: Path) -> tuple[str, ...]:
    # Windows paths compare without regard to case, wherever this runs.
    return tuple(part.casefold() for part in PureWindowsPath(path).parts)


def is_inside(path: Path, root: Path) -> bool:
    """Whether `path` is `root` or lies beneath it."""

    inner, outer = _parts(path), _parts(root)
    return inner[: len(outer)] == outer


def _folder_is_the_old_install(reading: LegacyReading) -> bool:
    location = reading.location
    return (
        location is not None
        and location.is_absolute()
        and reading.exists
        and reading.holds_exe
        and location.name.casefold() == LEGACY_APP_NAME.casefold()
    )


def plan_cleanup(reading: LegacyReading) -> LegacyPlan | None:
    """Decide what to remove; None when nothing of the old install is here."""

    if not reading.registered and not reading.exists and not reading.shortcuts:
        return None

    left_alone: list[str] = []
    folder: Path | None = None
    if _folder_is_the_old_install(reading):
        folder = reading.location
    elif reading.exists:
        left_alone.append(
            f"The folder {reading.location}, because it does not hold "
            f"{LEGACY_EXE_NAME}."
        )

    # The folder a shortcut must point into: the old install when it is being
    # removed; else the registered folder once it has already gone.
    gone = reading.location is not None and not reading.exists
    owned_root = folder if folder is not None else (reading.location if gone else None)

    registration = reading.registered and (folder is not None or not reading.exists)
    if reading.registered and not registration:
        left_alone.append(
            "Its entry in Apps, which stays so that folder can still be removed "
            "from there."
        )

    shortcuts: list[Path] = []
    for shortcut in reading.shortcuts:
        if (
            owned_root is not None
            and shortcut.target is not None
            and is_inside(shortcut.target, owned_root)
        ):
            shortcuts.append(shortcut.link)
        else:
            left_alone.append(
                f"The shortcut {shortcut.link}, because it does not point into "
                f"the old {LEGACY_APP_NAME} folder."
            )

    return LegacyPlan(
        version=reading.version,
        folder=folder,
        registration=registration,
        shortcuts=tuple(shortcuts),
        left_alone=tuple(left_alone),
    )


def describe(plan: LegacyPlan) -> str:
    """The confirmation text, naming every item to be removed and kept."""

    version = f" {plan.version}" if plan.version else ""
    lines = [
        (
            f"{logic.APP_DISPLAY_NAME} was previously called {LEGACY_APP_NAME}; "
            f"{LEGACY_APP_NAME}{version} is still installed on this PC."
        )
    ]
    removals: list[str] = []
    if plan.folder is not None:
        removals.append(f"The program folder {plan.folder}")
    removals.extend(f"The shortcut {link}" for link in plan.shortcuts)
    if plan.registration:
        removals.append("Its entry in Apps")
    if removals:
        lines.append("")
        lines.append("Setup can remove:")
        lines.extend(f"  • {item}" for item in removals)
    if plan.left_alone:
        lines.append("")
        lines.append("Left alone, for you to remove yourself if you wish:")
        lines.extend(f"  • {item}" for item in plan.left_alone)
    lines.append("")
    lines.append("Models you have saved elsewhere are not touched.")
    return "\n".join(lines)
