"""No pane is a keyboard stop, on any window or dialog in the app or installer.

Ported from NarrateX `tests/ui/test_panes_are_not_stops.py`. Focus belongs to
controls. A pane (a panel, a frame, a scroll area, a text view) holds them; a
ring on it tells the reader nothing and costs a key press to step past. The one
pane allowed is a reading pane while it overflows, by Tab only, since otherwise
the keyboard could not scroll it.

Three ways a pane gets focus, all checked, because a chain walk alone passed in
NarrateX while every licence opened ringed:

- the chain is walked FROM THE WINDOW, never from `focusWidget()`, since a walk
  from there skips the very widget the dialog opened on;
- a reading pane whose policy includes ClickFocus fails;
- a dialog whose `focusWidget()` just after `show()` is a reading pane fails.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabBar,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from simquence_ui.first_stop_dialog import FirstStopDialog, is_reading_pane_class

INSTALLER_DIR = Path(__file__).resolve().parents[1] / "installer"
_LONG_TEXT = "\n".join(f"line {n}" for n in range(400))
_CHAIN_LIMIT = 300
_MANY_PATHS = 60
_CONTROLS = (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSlider,
    QAbstractSpinBox,
    QComboBox,
    QLineEdit,
    QTabBar,
)


class _IdleController(QObject):
    started = Signal(int)
    succeeded = Signal(int, object)
    failed = Signal(int, str)
    cancelled = Signal(int, int)
    finished = Signal(int, float)

    def is_running(self) -> bool:
        return False

    def is_cancelled(self, _token: int) -> bool:
        return False

    def shutdown(self) -> None:
        return None


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> QApplication:
    """A QApplication whose static dialogs record rather than block.

    A static QMessageBox or QFileDialog builds a window nothing here can hide,
    so none may ever be built while the UI is driven.
    """

    calls: list[str] = []
    for name in ("question", "information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: calls.append(a))
    for name in ("getOpenFileName", "getSaveFileName"):
        monkeypatch.setattr(QFileDialog, name, lambda *a, **k: ("", ""))
    return QApplication.instance() or QApplication([])


def _show(window: QWidget) -> None:
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    QApplication.processEvents()


def _stops(window: QWidget) -> list[QWidget]:
    """Every stop in the window's chain, walked from the window itself."""

    seen, widget = [], window
    for _ in range(_CHAIN_LIMIT):
        widget = widget.nextInFocusChain()
        if widget is window:
            break
        if (
            widget.focusPolicy() & Qt.FocusPolicy.TabFocus
            and widget.isVisible()
            and widget.isEnabled()
        ):
            seen.append(widget)
    return seen


def _overflows(area) -> bool:
    return (
        area.verticalScrollBar().maximum() > 0
        or area.horizontalScrollBar().maximum() > 0
    )


def is_reading_pane(widget) -> bool:
    """A scroll area that is read: not an item view, not editable text."""

    if widget is None or not is_reading_pane_class(type(widget)):
        return False
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        return widget.isReadOnly()
    return True


def _is_neutral_start(widget) -> bool:
    """The keeb launch sinks: the main window itself, the installer's 0x0 one."""

    return isinstance(widget, QMainWindow) or type(widget).__name__ == "NeutralStart"


def pane_offence(stop) -> str | None:
    """Why `stop` should not be a stop; None when it is a legitimate one."""

    name = type(stop).__name__
    if isinstance(stop, _CONTROLS) or _is_neutral_start(stop):
        return None
    if isinstance(stop, (QTextEdit, QPlainTextEdit)) and not stop.isReadOnly():
        return None
    if is_reading_pane(stop):
        if stop.focusPolicy() & Qt.FocusPolicy.ClickFocus:
            return f"{name} is a reading pane a click would ring"
        if _overflows(stop):
            return None
        return f"{name} is a reading pane that scrolls nowhere"
    return f"{name} holds controls rather than being one"


def opening_focus(surface: QWidget, stops: list[QWidget]) -> QWidget | None:
    """The widget a dialog opens on.

    Offscreen never activates a window, so a dialog that leaves the choice to
    the platform opens with nothing focused here. On Windows activation hands
    focus to the first stop of the chain (measured: the installer licence with
    no focus of its own opened on its text), so that is what it is taken to be.
    """

    focused = surface.focusWidget()
    if focused is None and stops:
        return stops[0]
    return focused


def surface_offences(surfaces: list[QWidget]) -> list[str]:
    found = []
    for surface in surfaces:
        _show(surface)
        stops = _stops(surface)
        for stop in stops:
            offence = pane_offence(stop)
            if offence is not None:
                found.append(f"{type(surface).__name__}: {offence}")
        opened_on = opening_focus(surface, stops)
        if isinstance(surface, QDialog) and is_reading_pane(opened_on):
            found.append(f"{type(surface).__name__}: opens on its reading pane")
        surface.close()
    return found


def _app_surfaces() -> list[QWidget]:
    from simquence.version import __version__
    from simquence_ui.about_dialog import AboutDialog, AboutDialogContent
    from simquence_ui.critical_path_frequency_widget import (
        CriticalPathFrequencyWidget,
    )
    from simquence_ui.distributions_agg import CriticalPathBar
    from simquence_ui.guide_dialog import GuideDialog
    from simquence_ui.how_to_read_dialog import HowToReadDialog
    from simquence_ui.licence_dialog import LicenceDialog
    from simquence_ui.main_licence_dialog import MainLicenceDialog
    from simquence_ui.main_window import MainWindow
    from simquence_ui.main_window_menus import _about_text
    from simquence_ui.model_composer_dialog import ModelComposerDialog
    from simquence_ui.update_check import UpdatePromptDialog

    empty = MainWindow(run_controller=_IdleController())
    full = MainWindow(run_controller=_IdleController())
    full._summary_text.setPlainText(_LONG_TEXT)
    full._critical_path_text.setPlainText(_LONG_TEXT)
    frequency_holder = QWidget()
    frequency = CriticalPathFrequencyWidget(frequency_holder)
    QVBoxLayout(frequency_holder).addWidget(frequency)
    frequency.set_data(
        [CriticalPathBar(f"path {n}", f"path {n}", n) for n in range(_MANY_PATHS)]
    )

    return [
        empty,
        full,
        frequency_holder,
        AboutDialog(empty, content=AboutDialogContent(title="X", body=_about_text())),
        GuideDialog(empty),
        HowToReadDialog(empty),
        LicenceDialog(empty),
        MainLicenceDialog(empty),
        UpdatePromptDialog(empty, "99.0.0", __version__),
        ModelComposerDialog(empty),
    ]


def _installer_surfaces(monkeypatch: pytest.MonkeyPatch) -> list[QWidget]:
    monkeypatch.syspath_prepend(str(INSTALLER_DIR))
    import installer_lifecycle as lifecycle
    import installer_logic as logic
    from installer_widgets import AppRunningDialog, LicenceDialog, UninstallDialog
    from installer_window import InstallerWindow

    # Never read the registry: a fixed state that shows every action button.
    monkeypatch.setattr(lifecycle, "detect_state", lambda: logic.AppState.UPGRADE)
    window = InstallerWindow()
    return [
        window,
        LicenceDialog(_LONG_TEXT, "Licence", window),
        LicenceDialog("short", "Licence", window),
        AppRunningDialog("upgrade", window),
        UninstallDialog(window),
    ]


def test_no_app_surface_offers_a_pane_as_a_stop(app: QApplication) -> None:
    del app
    assert surface_offences(_app_surfaces()) == []


def test_no_installer_surface_offers_a_pane_as_a_stop(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    del app
    assert surface_offences(_installer_surfaces(monkeypatch)) == []


def test_the_composer_still_opens_on_its_section_tree(app: QApplication) -> None:
    from simquence_ui.model_composer_dialog import ModelComposerDialog
    from simquence_ui.model_composer_tree import ComposerTree

    del app
    holder = QMainWindow()
    composer = ModelComposerDialog(holder)
    _show(composer)
    assert isinstance(composer.focusWidget(), ComposerTree)
    composer.close()


def test_the_walk_catches_each_way_a_pane_takes_focus(app: QApplication) -> None:
    """The guard bites: each planted pane is named, each control is spared."""

    del app
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    layout.addWidget(QScrollArea(dialog))
    layout.addWidget(QPushButton("Close", dialog))
    fits = QTextBrowser(dialog)
    fits.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    layout.addWidget(fits)
    layout.addWidget(QTextEdit(dialog))
    clickable = QTextBrowser(dialog)
    clickable.setPlainText(_LONG_TEXT)
    layout.addWidget(clickable)
    _show(dialog)
    assert [pane_offence(stop) for stop in _stops(dialog)] == [
        "QScrollArea is a reading pane a click would ring",
        None,
        "QTextBrowser is a reading pane that scrolls nowhere",
        None,
        "QTextBrowser is a reading pane a click would ring",
    ]
    dialog.close()


class _NoReadingPaneSkip(FirstStopDialog):
    """The 3.3.0 dialog: its first stop could be a reading pane (the defect)."""

    def _is_stop(self, widget: QWidget) -> bool:
        return (
            widget is not self
            and self.isAncestorOf(widget)
            and widget.isEnabled()
            and widget.isVisible()
            and bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)
        )


def test_a_dialog_opens_on_its_control_never_on_its_pane(app: QApplication) -> None:
    """Without the skip a dialog opens on its page; with it, on its control."""

    from simquence_ui.pane_focus import follow_overflow

    del app
    found = {}
    for dialog_class in (_NoReadingPaneSkip, FirstStopDialog):
        dialog = dialog_class()
        layout = QVBoxLayout(dialog)
        text = QTextBrowser(dialog)
        text.setPlainText(_LONG_TEXT)
        layout.addWidget(text)
        follow_overflow(text)
        layout.addWidget(QPushButton("Close", dialog))
        found[dialog_class.__name__] = surface_offences([dialog])
    assert found == {
        "_NoReadingPaneSkip": ["_NoReadingPaneSkip: opens on its reading pane"],
        "FirstStopDialog": [],
    }
