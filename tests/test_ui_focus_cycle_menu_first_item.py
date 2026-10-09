"""A menu the ring drops offers its first usable item, as Down already does.

Qt drops a title's menu the moment the ring highlights it and opens it with
nothing active, so the user who arrived there had to press Down before anything
was offered (measured on Windows and offscreen alike).
"""

from __future__ import annotations

import pytest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QPushButton

from simquence_ui.focus_cycle import FocusCycleController
from simquence_ui.focus_cycle_menu import highlight_first_item


@pytest.fixture()
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(app: QApplication):
    w = QMainWindow()
    w.setCentralWidget(QPushButton("x"))
    file_menu = w.menuBar().addMenu("File")
    file_menu.addSeparator()
    disabled = file_menu.addAction("Disabled")
    disabled.setEnabled(False)
    hidden = file_menu.addAction("Hidden")
    hidden.setVisible(False)
    file_menu.addAction("Open")
    file_menu.addAction("Save")
    w.menuBar().addMenu("Help").addAction("Guide")
    cycle = FocusCycleController(w)
    w._cycle = cycle
    w.show()
    w.activateWindow()
    cycle.install()
    app.processEvents()
    yield w
    popup = QApplication.activePopupWidget()
    if popup is not None:
        popup.close()
    cycle.uninstall()
    w.close()


def _settle(app: QApplication) -> None:
    for _ in range(3):
        app.processEvents()


def test_the_ring_drops_a_menu_with_its_first_usable_item_offered(
    app: QApplication, window: QMainWindow
) -> None:
    QTest.keyClick(window, Qt.Key.Key_Tab)
    _settle(app)
    popup = QApplication.activePopupWidget()
    assert isinstance(popup, QMenu) and popup.title() == "File"
    assert popup.activeAction().text() == "Open"


def test_carrying_the_drop_along_the_bar_offers_the_next_menus_first_item(
    app: QApplication, window: QMainWindow
) -> None:
    QTest.keyClick(window, Qt.Key.Key_Tab)
    _settle(app)
    QTest.keyClick(QApplication.activePopupWidget(), Qt.Key.Key_Right)
    _settle(app)
    popup = QApplication.activePopupWidget()
    assert popup.title() == "Help"
    assert popup.activeAction().text() == "Guide"


def test_a_stale_offer_is_ignored_once_the_ring_has_moved_on(
    app: QApplication, window: QMainWindow
) -> None:
    file_action = window.menuBar().actions()[0]
    file_menu = file_action.menu()
    file_menu.popup(window.mapToGlobal(window.rect().center()))
    _settle(app)
    file_menu.setActiveAction(None)
    window._cycle._pending_stop = None
    window._cycle._offer_first_item(file_action)
    assert file_menu.activeAction() is None


def test_nothing_to_offer_when_there_is_no_menu_or_it_is_shut(
    app: QApplication,
) -> None:
    highlight_first_item(None)
    shut = QMenu()
    shut.addAction("one")
    highlight_first_item(shut)
    assert shut.activeAction() is None


def test_a_menu_already_offering_an_item_is_left_alone(app: QApplication) -> None:
    menu = QMenu()
    menu.addAction("one")
    second = menu.addAction("two")
    menu.popup(menu.pos())
    app.processEvents()
    menu.setActiveAction(second)
    highlight_first_item(menu)
    assert menu.activeAction() is second
    menu.close()


def test_a_menu_with_nothing_usable_offers_nothing(app: QApplication) -> None:
    menu = QMenu()
    menu.addSeparator()
    inert = menu.addAction("inert")
    inert.setEnabled(False)
    menu.popup(menu.pos())
    app.processEvents()
    highlight_first_item(menu)
    assert menu.activeAction() is None
    menu.close()
