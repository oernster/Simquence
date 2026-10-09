"""Locate the generated icon assets, whatever the app was packaged with.

`assets/` sits beside the source tree in development, beside the executable in a
Nuitka standalone build, under `Contents/Resources` in a macOS bundle and at
`/app/assets` inside a Flatpak. The code that wants an icon should not know any
of that, so every caller asks here.

The search itself is not icon-specific and lives in `packaged_dir`; what this
module adds is which directory to look for and what the files inside it are
called.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from simquence_ui.packaged_dir import (
    FLATPAK_ROOT,
    bundle_dir,
    candidate_dirs,
    compiled_dir,
    executable_dir,
    first_existing_dir,
    source_root,
)

ASSETS_DIR_NAME = "assets"

# An escape hatch for anyone running the UI from an unusual layout. It is
# also the hook the tests use to prove the override wins.
ASSETS_DIR_ENV_VAR = "SIMQUENCE_ASSETS_DIR"

# Flatpak stages the app under /app, so the assets land at a fixed path.
FLATPAK_ASSETS_DIR = FLATPAK_ROOT / ASSETS_DIR_NAME

ICO_NAME = "simquence.ico"
PNG_STEM = "simquence_icon"
CANONICAL_PNG_NAME = f"{PNG_STEM}.png"

# The same mark flattened onto opaque black, generated only for macOS. The Dock
# composites the icon onto the desktop, so the transparent version reads as red
# and yellow on the pale grey behind it. See generate_icons.py.
MAC_PNG_STEM = f"{PNG_STEM}_mac"
MAC_CANONICAL_PNG_NAME = f"{MAC_PNG_STEM}.png"
MACOS_PLATFORM = "darwin"

# The sizes generate_icons.py writes. Kept here so a caller asking for a size
# that was never generated gets the nearest one that was, rather than a path
# that does not exist.
AVAILABLE_PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)

# What the About badge and the installer window ask for.
BADGE_PNG_SIZE = 256

# The donate mark, derived by generate_icons.py from the donate.png master at
# the repository root, so a build ships the small render and never the master.
DONATE_PNG_NAME = "donate.png"

# The top bar's artwork, one picture per action. Supplied finished rather than
# generated, so they are read as they are.
SAVE_EXPORT_ART = "simquence_save_export.png"
# Named for what they show, not for their file names, which point the other way:
# the "i" in a circle is the Guide's picture and the open book is How to Read's.
INFO_ART = "simquence_output_information.png"
BOOK_ART = "simquence_guide.png"
COMPOSE_ART = "simquence_compose_model.png"
OPEN_EDIT_ART = "simquence_open_edit.png"
DISTRIBUTIONS_ART = "simquence_distributions.png"


def candidate_asset_dirs(
    *,
    env_value: str | None,
    executable_dir: Path | None,
    compiled_dir: Path | None,
    source_root: Path,
    bundle_dir: Path | None = None,
    flatpak_dir: Path = FLATPAK_ASSETS_DIR,
) -> tuple[Path, ...]:
    """Every place `assets/` could be, most specific first."""

    return candidate_dirs(
        dir_name=ASSETS_DIR_NAME,
        env_value=env_value,
        executable_dir=executable_dir,
        compiled_dir=compiled_dir,
        source_root=source_root,
        bundle_dir=bundle_dir,
        flatpak_dir=flatpak_dir,
    )


def find_assets_dir(candidates: tuple[Path, ...] | None = None) -> Path | None:
    """The first candidate directory that exists; None if none do."""

    if candidates is None:
        candidates = candidate_asset_dirs(
            env_value=os.environ.get(ASSETS_DIR_ENV_VAR),
            executable_dir=executable_dir(),
            compiled_dir=compiled_dir(),
            source_root=source_root(),
            bundle_dir=bundle_dir(),
        )

    return first_existing_dir(candidates)


def nearest_available_size(size: int) -> int:
    """The generated size closest to `size`.

    Ties go to the larger of the two, because downscaling a slightly-too-big
    icon looks better than upscaling a slightly-too-small one.
    """

    return min(
        AVAILABLE_PNG_SIZES, key=lambda available: (abs(available - size), -available)
    )


def app_icon_names(platform: str = sys.platform) -> tuple[str, ...]:
    """The icon filenames to try for the Dock, taskbar and window, best first.

    macOS gets the opaque variant ahead of everything else, because its Dock
    draws the icon straight onto the desktop. Windows wants the `.ico` so the
    taskbar and Explorer can pick their own frame. The transparent canonical
    PNG is the last resort everywhere and covers the case where
    generate_icons.py has not been run.
    """

    if platform == MACOS_PLATFORM:
        return (MAC_CANONICAL_PNG_NAME, ICO_NAME, CANONICAL_PNG_NAME)
    return (ICO_NAME, CANONICAL_PNG_NAME)


def get_app_icon_path(
    assets_dir: Path | None = None, platform: str = sys.platform
) -> Path | None:
    """The first icon file this platform wants that actually exists."""

    if assets_dir is None:
        assets_dir = find_assets_dir()
    if assets_dir is None:
        return None

    for name in app_icon_names(platform):
        candidate = assets_dir / name
        if candidate.is_file():
            return candidate
    return None


def get_app_icon_png_path(
    size: int = BADGE_PNG_SIZE, assets_dir: Path | None = None
) -> Path | None:
    """The generated PNG nearest to `size`; None when the set is absent."""

    if assets_dir is None:
        assets_dir = find_assets_dir()
    if assets_dir is None:
        return None

    candidate = assets_dir / f"{PNG_STEM}_{nearest_available_size(size)}.png"
    return candidate if candidate.is_file() else None


def get_asset_path(file_name: str, assets_dir: Path | None = None) -> Path | None:
    """A named file in the assets directory; None when it is not there."""

    if assets_dir is None:
        assets_dir = find_assets_dir()
    if assets_dir is None:
        return None

    candidate = assets_dir / file_name
    return candidate if candidate.is_file() else None


def get_donate_png_path(assets_dir: Path | None = None) -> Path | None:
    """The artwork for the donate button; None when it was never generated."""

    return get_asset_path(DONATE_PNG_NAME, assets_dir)
