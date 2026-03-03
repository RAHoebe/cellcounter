"""
about_dialog.py
AboutDialog — mirrors frmAbout.frm.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class AboutDialog(QDialog):

    def __init__(self, version: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("About CellCounter")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setFixedWidth(500)
        self.setSizeGripEnabled(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        lbl_title = QLabel("CellCounter")
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(lbl_title)

        # Version
        lbl_ver = QLabel(f"Version {version}")
        lbl_ver.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(lbl_ver)

        # Description
        lbl_desc = QLabel(
            "Use selected keys to update a Counter.\n"
            "Key = +1    Shift+Key = −1    Ctrl+Key = Reset to 0\n"
            "R = Reset all counters to zero\n"
            "Alarm values can be set, alarm sound can be configured.\n"
            "Sound, defaults, key assignments and names are saved per settings slot.\n\n"
            "Key mode (bottom bar):\n"
            "  Local  — keys register only when CellCounter has focus\n"
            "  Global — keys register system-wide, even when another application has focus"
        )
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Divider
        layout.addWidget(self._make_divider())

        # Contact
        email_lbl = QLabel(
            '<a href="mailto:R.A.Hoebe@amsterdamumc.nl">R.A.Hoebe@amsterdamumc.nl</a>'
        )
        email_lbl.setOpenExternalLinks(True)
        email_lbl.setStyleSheet("color: red;")
        layout.addWidget(email_lbl)

        # Divider
        layout.addWidget(self._make_divider())

        # Disclaimer
        lbl_copy = QLabel(
            "Copyright (c) 2008 - 2026, Ron Hoebe\n"
            "Amsterdam UMC, The Netherlands"
        )
        lbl_copy.setFont(QFont("Arial", 8))
        layout.addWidget(lbl_copy)

        layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_sysinfo = QPushButton("System Info")
        btn_sysinfo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_sysinfo.clicked.connect(self._launch_sysinfo)
        btn_row.addWidget(btn_sysinfo)
        btn_row.addStretch()
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    @staticmethod
    def _make_divider() -> QWidget:
        line = QWidget()
        line.setFixedHeight(2)
        line.setStyleSheet("background: #A0A0A0;")
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return line

    def _launch_sysinfo(self):
        import subprocess  # noqa: PLC0415
        try:
            subprocess.Popen(["msinfo32.exe"])
        except FileNotFoundError:
            pass
