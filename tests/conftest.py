from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _qt_offscreen() -> None:
    """Ensure Qt can initialize in CI/headless environments."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def _add_repo_root_to_syspath() -> None:
    """Make local packages importable when running tests from `tests/`.

    Some Windows/PyTest invocations end up with `tests/` as the import root.
    Ensure the repo root is on `sys.path` so `import latencylab_ui` works.
    """

    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


@pytest.fixture(autouse=True)
def _delete_leftover_windows():
    """Delete every window a test leaves behind, through Qt, as it ends.

    Tests build parentless windows and dialogs and walk away from them. Many
    sit in reference cycles (a controller parented to its window that keeps a
    reference back), so they used to die whenever the cyclic garbage collector
    next ran. That could be inside a later test's processEvents, in the middle
    of a focusChanged emission whose arguments were the widgets being freed;
    the suite then died with heap corruption in test_ui_focus_cycle.py.
    Deleting them here, at a quiet point and in Qt's own order, leaves the
    collector nothing that still owns a live Qt object.
    """

    yield
    # Never import Qt here: some tests run with PySide6 hidden on purpose.
    widgets = sys.modules.get("PySide6.QtWidgets")
    if widgets is None:
        return
    app = widgets.QApplication.instance()
    if app is None:
        return
    from PySide6.QtCore import QCoreApplication, QEvent

    for window in app.topLevelWidgets():
        if window.parentWidget() is None:
            window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
