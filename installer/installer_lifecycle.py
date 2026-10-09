"""Install, repair and uninstall, composed from the decisions and the effects.

Each function here is one complete action: it reads the payload, deploys or
removes files, writes or clears the registration and puts the shortcuts where
the user asked for them.
"""

from __future__ import annotations

from pathlib import Path

import installer_bundle as bundle
import installer_legacy as legacy
import installer_logic as logic
import installer_ops as ops
import installer_payload as payload


def detect_state() -> str:
    """Classify this machine against the version in the payload."""

    installed, location = ops.read_installed()
    return logic.detect_state(installed, location, bundle.app_version())


def primary_label(state: str) -> str:
    return logic.primary_label(state, bundle.app_version())


def install(target: Path, *, desktop: bool, start_menu: bool) -> Path:
    """Deploy the application, register it and create the chosen shortcuts."""

    exe_path = payload.deploy_files(
        payload.payload_archive(bundle.bundle_root()), target
    )

    uninstaller = logic.uninstaller_path(target)
    uninstaller.parent.mkdir(parents=True, exist_ok=True)
    _copy_installer(uninstaller)

    ops.write_uninstall_entry(
        logic.uninstall_entry_values(
            target,
            uninstaller,
            bundle.app_version() or logic.FALLBACK_VERSION,
            logic.dir_size_kb(target),
        )
    )

    icon = target / logic.ASSETS_DIR_NAME / logic.SHORTCUT_ICON_FILE_NAME
    resolved_icon = icon if icon.is_file() else None

    if desktop:
        ops.create_shortcut(ops.desktop_link(), exe_path, resolved_icon)
    else:
        ops.remove_shortcut(ops.desktop_link())

    start_menu_link = ops.start_menu_link()
    if start_menu and start_menu_link is not None:
        ops.create_shortcut(start_menu_link, exe_path, resolved_icon)
    elif start_menu_link is not None:
        ops.remove_shortcut(start_menu_link)

    return exe_path


def _copy_installer(destination: Path) -> None:
    """Keep a copy of this setup program so Apps and features can re-run it."""

    import shutil

    source = ops.running_installer_exe()
    if source.is_file() and source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def repair(location: Path) -> Path:
    """Re-deploy the application files over an existing install."""

    return install(location, desktop=False, start_menu=False)


def uninstall() -> None:
    """Remove the application, its shortcuts and its registration."""

    _, location = ops.read_installed()
    target = location or ops.install_target()

    ops.remove_shortcut(ops.desktop_link())
    ops.remove_shortcut(ops.start_menu_link())
    ops.delete_uninstall_entry()

    ops.remove_tree_except(target, logic.UNINSTALLER_SUBDIR)
    ops.schedule_self_delete(target)


def find_legacy() -> legacy.LegacyPlan | None:
    """Read the install left under the old name; None when there is none."""

    version, location = ops.read_installed(legacy.LEGACY_UNINSTALL_KEY)
    if location is None:
        location = ops.install_target(legacy.LEGACY_APP_NAME)
    links = (
        ops.desktop_link(legacy.LEGACY_APP_NAME),
        ops.start_menu_link(legacy.LEGACY_APP_NAME),
    )
    reading = legacy.LegacyReading(
        registered=ops.registration_exists(legacy.LEGACY_UNINSTALL_KEY),
        version=version,
        location=location,
        exists=location.is_dir(),
        holds_exe=(location / legacy.LEGACY_EXE_NAME).is_file(),
        shortcuts=tuple(
            legacy.LegacyShortcut(link, ops.shortcut_target(link))
            for link in links
            if link is not None and link.is_file()
        ),
    )
    return legacy.plan_cleanup(reading)


def remove_legacy(plan: legacy.LegacyPlan) -> None:
    """Carry out a plan. The folder goes first: should it fail, the Apps entry
    is still there for the user to remove it from."""

    if plan.folder is not None:
        ops.remove_tree(plan.folder)
    for link in plan.shortcuts:
        ops.remove_shortcut(link)
    if plan.registration:
        ops.delete_uninstall_entry(legacy.LEGACY_UNINSTALL_KEY)
