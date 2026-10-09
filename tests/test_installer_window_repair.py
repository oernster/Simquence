"""Repair honours "Launch when finished", exactly as Install does.

It used to put the files back and stop, whatever the box said, so a user who
asked for the application got a finished setup window instead. The registry,
the process list and the file work are stood in for; the window's own decision
is what is under test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "installer"
if str(INSTALLER_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALLER_DIR))

import installer_lifecycle as lifecycle  # noqa: E402
import installer_logic as logic  # noqa: E402
import installer_ops as ops  # noqa: E402
from installer_window import InstallerWindow  # noqa: E402


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def repaired(app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    exe = tmp_path / logic.EXE_NAME
    monkeypatch.setattr(lifecycle, "detect_state", lambda: logic.AppState.REINSTALL)
    monkeypatch.setattr(ops, "is_app_running", lambda *_args: False)
    monkeypatch.setattr(ops, "read_installed", lambda *_args: ("1.0.0", tmp_path))
    monkeypatch.setattr(lifecycle, "repair", lambda _location: exe)

    window = InstallerWindow()
    launched: list[Path] = []
    monkeypatch.setattr(window, "_launch_and_front", launched.append)
    yield window, exe, launched
    window.deleteLater()


def test_repair_launches_the_application_when_asked(repaired) -> None:
    window, exe, launched = repaired
    window._launch_on_finish.setChecked(True)

    window._on_repair()

    assert launched == [exe]


def test_repair_leaves_the_application_closed_when_not_asked(repaired) -> None:
    window, _exe, launched = repaired
    window._launch_on_finish.setChecked(False)

    window._on_repair()

    assert launched == []
