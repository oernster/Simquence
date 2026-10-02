"""Handing an address to the desktop, behind one function.

This seam exists for a testing reason: calling Qt's opener straight from the
top bar would leave no way to prove the right address is asked for without
either mocking Qt or opening a real browser in the middle of a test run. The
application never fetches the page itself; the desktop's browser does the
asking, so nothing in LatencyLab opens a connection because the button exists.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_externally(address: str) -> bool:
    """Ask the desktop to open this address; False when it declined to."""

    return QDesktopServices.openUrl(QUrl(address))
