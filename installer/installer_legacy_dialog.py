"""The confirmation for clearing away the install left under the old name.

It names every item it would remove and every item it found but will leave
alone, so nothing disappears that the user was not shown. When nothing can be
shown to be the old install's own, there is nothing to confirm: the dialog only
reports, with a single button.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import installer_bundle as bundle
import installer_legacy as legacy
import installer_theme as theme
from installer_keys import FirstStopDialog


class LegacyCleanupDialog(FirstStopDialog):
    """Ask whether to remove the old install; Accepted means remove it."""

    def __init__(self, plan: legacy.LegacyPlan, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Remove {legacy.LEGACY_APP_NAME}")
        self.setWindowIcon(bundle.app_icon())
        self.setStyleSheet(theme.STYLESHEET)

        layout = QVBoxLayout(self)
        margin = theme.DIALOG_MARGIN
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.BUTTON_GAP)

        message = QLabel(legacy.describe(plan))
        message.setWordWrap(True)
        layout.addWidget(message)

        row = QHBoxLayout()
        row.addStretch()
        if plan.removes_anything:
            keep = QPushButton(f"Keep {legacy.LEGACY_APP_NAME}")
            keep.setObjectName("SecondaryAction")
            keep.clicked.connect(self.reject)
            remove = QPushButton(f"Remove {legacy.LEGACY_APP_NAME}")
            remove.setObjectName("DangerAction")
            remove.clicked.connect(self.accept)
            row.addWidget(keep)
            row.addWidget(remove)
        else:
            close = QPushButton("OK")
            close.setObjectName("SecondaryAction")
            close.clicked.connect(self.reject)
            row.addWidget(close)
        layout.addLayout(row)
