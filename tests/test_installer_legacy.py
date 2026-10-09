"""Tests for clearing away the install left under the product's old name.

What may be removed is decided from a reading of the machine, never from the
machine itself, so every rule is asserted here: the folder only when it is the
old install, a shortcut only when it points into it, the Apps entry only with
the folder or once its folder is gone. Everything else is reported and kept.
"""

from __future__ import annotations

import sys
from pathlib import Path

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "installer"
if str(INSTALLER_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALLER_DIR))

import installer_legacy as legacy  # noqa: E402
import installer_logic as logic  # noqa: E402

OLD = Path("C:/Users/u/AppData/Local/Programs/LatencyLab")
DESKTOP = Path("C:/Users/u/Desktop/LatencyLab.lnk")
START = Path("C:/Users/u/AppData/Roaming/Start Menu/LatencyLab.lnk")


def reading(**overrides) -> legacy.LegacyReading:
    values = {
        "registered": True,
        "version": "3.3.2",
        "location": OLD,
        "exists": True,
        "holds_exe": True,
        "shortcuts": (),
    }
    values.update(overrides)
    return legacy.LegacyReading(**values)


def shortcut(link: Path, target: Path | None) -> legacy.LegacyShortcut:
    return legacy.LegacyShortcut(link, target)


def test_the_old_key_is_the_old_name_under_the_same_root() -> None:
    assert legacy.LEGACY_UNINSTALL_KEY == logic.uninstall_key("LatencyLab")
    assert legacy.LEGACY_UNINSTALL_KEY.endswith("\\LatencyLab")
    assert legacy.LEGACY_UNINSTALL_KEY != logic.UNINSTALL_KEY


def test_nothing_of_the_old_install_means_no_plan() -> None:
    nothing = reading(registered=False, version=None, exists=False, holds_exe=False)
    assert legacy.plan_cleanup(nothing) is None


def test_a_proven_install_goes_with_its_entry_and_its_own_shortcuts() -> None:
    plan = legacy.plan_cleanup(
        reading(
            shortcuts=(
                shortcut(DESKTOP, OLD / "LatencyLab.exe"),
                # Windows paths compare without regard to case.
                shortcut(START, Path(str(OLD).upper()) / "LATENCYLAB.EXE"),
            )
        )
    )

    assert plan is not None
    assert plan.folder == OLD
    assert plan.registration
    assert plan.shortcuts == (DESKTOP, START)
    assert plan.left_alone == ()
    assert plan.removes_anything


def test_a_shortcut_pointing_anywhere_else_is_kept_and_named() -> None:
    elsewhere = Path("C:/Tools/LatencyLab.exe")
    plan = legacy.plan_cleanup(
        reading(shortcuts=(shortcut(DESKTOP, elsewhere), shortcut(START, None)))
    )

    assert plan is not None
    assert plan.shortcuts == ()
    assert any(str(DESKTOP) in line for line in plan.left_alone)
    assert any(str(START) in line for line in plan.left_alone)


def test_a_folder_without_the_old_program_is_kept_with_its_entry() -> None:
    plan = legacy.plan_cleanup(
        reading(holds_exe=False, shortcuts=(shortcut(DESKTOP, OLD / "x.exe"),))
    )

    assert plan is not None
    assert plan.folder is None
    assert not plan.registration
    assert plan.shortcuts == ()
    assert not plan.removes_anything
    assert any(str(OLD) in line for line in plan.left_alone)
    assert any("Apps" in line for line in plan.left_alone)


def test_a_folder_not_named_for_the_old_product_is_kept() -> None:
    plan = legacy.plan_cleanup(reading(location=Path("C:/Users/u/Documents")))

    assert plan is not None
    assert plan.folder is None
    assert not plan.registration


def test_a_relative_location_is_never_removed() -> None:
    plan = legacy.plan_cleanup(reading(location=Path("LatencyLab")))

    assert plan is not None
    assert plan.folder is None


def test_an_entry_whose_folder_is_gone_goes_with_shortcuts_into_it() -> None:
    plan = legacy.plan_cleanup(
        reading(
            exists=False,
            holds_exe=False,
            shortcuts=(shortcut(DESKTOP, OLD / "LatencyLab.exe"),),
        )
    )

    assert plan is not None
    assert plan.folder is None
    assert plan.registration
    assert plan.shortcuts == (DESKTOP,)
    assert plan.left_alone == ()


def test_an_unregistered_folder_still_goes_without_touching_the_registry() -> None:
    plan = legacy.plan_cleanup(reading(registered=False, version=None))

    assert plan is not None
    assert plan.folder == OLD
    assert not plan.registration


def test_a_sibling_sharing_the_prefix_is_not_inside() -> None:
    assert legacy.is_inside(OLD / "assets" / "a.ico", OLD)
    assert legacy.is_inside(OLD, OLD)
    assert not legacy.is_inside(OLD.parent / "LatencyLab2" / "x.exe", OLD)
    assert not legacy.is_inside(OLD.parent, OLD)


def test_the_confirmation_names_every_item_and_the_version() -> None:
    plan = legacy.plan_cleanup(
        reading(
            shortcuts=(
                shortcut(DESKTOP, OLD / "LatencyLab.exe"),
                shortcut(START, Path("C:/Tools/x.exe")),
            )
        )
    )
    assert plan is not None
    text = legacy.describe(plan)

    assert "LatencyLab 3.3.2" in text
    assert str(OLD) in text
    assert str(DESKTOP) in text
    assert "Apps" in text
    assert "Left alone" in text and str(START) in text
    assert "\u2014" not in text and "\u2013" not in text


def test_a_report_only_plan_offers_nothing_to_remove() -> None:
    plan = legacy.plan_cleanup(reading(holds_exe=False, version=None))
    assert plan is not None
    text = legacy.describe(plan)

    assert "Setup can remove" not in text
    assert "Left alone" in text
    assert "LatencyLab is still installed" in text
