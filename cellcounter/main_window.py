"""
main_window.py
CellCounterWindow — QMainWindow orchestrating the full application.
Mirrors frmCount.frm in the VB6 source.

Key behaviours reproduced:
  • Up to 16 counters in a 4-column grid, shown/hidden based on useCounters (4/8/12/16)
  • 8 named settings slots (load/save via SettingsStore)
  • local keyboard capture: bare key=+1, Shift=−1, Ctrl=reset-to-0
  • 'R' key (any modifier) = confirm-reset all counters
  • Per-counter alarms and sum alarm (fire on exact threshold, incrementing only)
  • Keyclick sound toggle
  • Tab-delimited session log with millisecond timestamps
  • Save CSV, Save TAB-delimited, Save Log, Copy sums/log/form to clipboard
  • Context menu on sum label: copy sum value
  • Colour/name/alarm customisation via context menus on counter widgets
"""

from __future__ import annotations

import csv
import io
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QFont, QIcon, QKeyEvent, QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cellcounter.counter_widget import CounterWidget
from cellcounter.key_map import ALARM_NAMES, KEY_LIST
from cellcounter.logger import DataLogger
from cellcounter.settings import NUM_COUNTERS, NUM_SLOTS, SettingsStore
from cellcounter.sound import SoundPlayer


def _read_version() -> str:
    """Read version string from version.txt in the project/bundle root."""
    candidates = [
        Path(__file__).parent.parent / "version.txt",  # dev layout
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys._MEIPASS) / "version.txt")
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return "unknown"


_APP_VERSION = _read_version()


class CellCounterWindow(QMainWindow):

    NUM_COUNTERS = NUM_COUNTERS   # 16

    def __init__(self):
        super().__init__()

        self._store = SettingsStore()
        self._sound = SoundPlayer()
        self._logger = DataLogger(self._store.data_dir())
        self._current_slot = 1
        self._use_counters = 4        # active counter count
        self._loading = False         # suppress saves during load

        # Build UI first (so _sound.ensure_loaded() has a live QApplication)
        self._counters: list[CounterWidget] = []
        self._build_ui()
        self._sound.ensure_loaded()

        # Configure window flags & icon before loading settings
        self._configure_window()

        # Now load settings (may call _apply_counter_count)
        self._load_slot(1)

    # ==================================================================
    # Window setup
    # ==================================================================

    def _configure_window(self):
        self.setWindowTitle("CellCounter")
        # No maximize button, fixed-width feel
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setMinimumWidth(1230)
        self.setMaximumWidth(1230)

        # Re-apply the application icon after setWindowFlags (flags reset clears it)
        app_icon = QApplication.instance().windowIcon()
        if app_icon and not app_icon.isNull():
            self.setWindowIcon(app_icon)

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self):
        self._build_menus()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # --- Counter grid ---
        self._grid_widget = QWidget()
        self._grid_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(4)

        for i in range(NUM_COUNTERS):
            w = CounterWidget(i)
            w.alarm_triggered.connect(self._on_alarm_triggered)
            w.value_changed.connect(self._on_value_changed)
            # Wire per-counter config-change signals to save
            w.cmb_key.currentIndexChanged.connect(lambda _, idx=i: self._save_current_slot())
            w.cmb_alarm.currentIndexChanged.connect(lambda _, idx=i: self._save_current_slot())
            w.alarm_value_changed.connect(lambda idx=i: self._save_current_slot())
            w.chk_add.stateChanged.connect(lambda _, idx=i: self._save_current_slot())
            self._counters.append(w)
            col = i % 4
            row = i // 4
            self._grid.addWidget(w, row, col)

        root.addWidget(self._grid_widget, stretch=0)

        # --- Bottom bar ---
        self._bottom_bar = self._build_bottom_bar()
        self._bottom_bar.setFixedHeight(34)
        root.addWidget(self._bottom_bar, stretch=0)

    def _build_menus(self):
        mb = self.menuBar()

        # File
        m_file = mb.addMenu("&File")
        m_file.addAction("Save Sums to File (Excel format)…",  self._save_tab)
        m_file.addAction("Save Sums to CSV File (.csv)…",      self._save_csv)
        m_file.addAction("Save Log to File…",                   self._save_log)
        m_file.addSeparator()
        m_file.addAction("E&xit", self.close)

        # Edit
        m_edit = mb.addMenu("&Edit")
        m_edit.addAction("Copy Sums to Clipboard (Excel format)", self._copy_sums_clipboard)
        m_edit.addAction("Copy Log to Clipboard",                  self._copy_log_clipboard)
        m_edit.addAction("Copy Form to Clipboard (Bitmap)",        self._copy_form_bitmap)

        # Format
        m_fmt = mb.addMenu("F&ormat")
        m_fmt.addAction("Rename Current Settings Slot…", self._rename_slot)
        m_fmt.addAction("Edit Sum Alarm Value…",          self._edit_sum_alarm)

        # Help
        m_help = mb.addMenu("&Help")

        m_help.addAction("About…", self._show_about)

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        bar.setObjectName("bottom_bar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(6)

        # -- Counters selector --
        layout.addWidget(QLabel("Counters:"))
        self.cmb_num = QComboBox()
        self.cmb_num.addItems(["4", "8", "12", "16"])
        self.cmb_num.setFixedWidth(50)
        self.cmb_num.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cmb_num.currentIndexChanged.connect(self._on_num_changed)
        layout.addWidget(self.cmb_num)

        # -- Custom settings slot selector --
        layout.addWidget(QLabel("Custom Settings:"))
        self.cmb_custom = QComboBox()
        self.cmb_custom.setMinimumWidth(130)
        self.cmb_custom.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cmb_custom.currentIndexChanged.connect(self._on_slot_changed)
        layout.addWidget(self.cmb_custom)

        # -- Keyclick checkbox --
        self.chk_sound = QCheckBox("Keyclick")
        self.chk_sound.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_sound.stateChanged.connect(self._on_keyclick_changed)
        layout.addWidget(self.chk_sound)

        # -- Sum alarm sound --
        self.cmb_sum_alarm = QComboBox()
        for name in ALARM_NAMES:
            self.cmb_sum_alarm.addItem(name)
        self.cmb_sum_alarm.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cmb_sum_alarm.currentIndexChanged.connect(lambda _: self._save_current_slot())
        layout.addWidget(self.cmb_sum_alarm)

        # -- Sum alarm threshold --
        layout.addWidget(QLabel("Sum Alarm:"))
        self._sum_alarm_value = 100
        self.lbl_sum_alarm = QLabel("100")
        self.lbl_sum_alarm.setFixedWidth(55)
        self.lbl_sum_alarm.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_sum_alarm.setStyleSheet(
            "background: #FFE0E0; border: 1px solid #808080; padding: 1px 4px;"
        )
        self.lbl_sum_alarm.setToolTip("Sum alarm threshold")
        layout.addWidget(self.lbl_sum_alarm)

        btn_edit_sum = QPushButton("...")
        btn_edit_sum.setFixedSize(26, 22)
        btn_edit_sum.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_edit_sum.setToolTip("Edit sum alarm value")
        btn_edit_sum.clicked.connect(self._edit_sum_alarm)
        layout.addWidget(btn_edit_sum)

        # -- Sum progress bar --
        self.sum_progress = QProgressBar()
        self.sum_progress.setRange(0, 100)
        self.sum_progress.setValue(0)
        self.sum_progress.setTextVisible(True)
        self.sum_progress.setFormat("%p %")
        self.sum_progress.setFixedWidth(60)
        self.sum_progress.setFixedHeight(18)
        self.sum_progress.setStyleSheet(
            "QProgressBar { border: 1px solid #808080; border-radius: 2px; background: #F0F0F0; text-align: center; }"
            "QProgressBar::chunk { background: #FF0000; border-radius: 1px; }"
        )
        layout.addWidget(self.sum_progress)

        # -- Counters Sum display --
        layout.addWidget(QLabel("Counters Sum:"))
        self.lbl_sum = QLabel("0")
        self.lbl_sum.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.lbl_sum.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_sum.setMinimumWidth(60)
        self.lbl_sum.setStyleSheet(
            "background: #EAFFEA; color: #006600; border: 1px solid #808080; padding: 2px 6px;"
        )
        self.lbl_sum.setToolTip("Right-click to copy sum to clipboard")
        self.lbl_sum.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lbl_sum.customContextMenuRequested.connect(self._sum_context_menu)
        layout.addWidget(self.lbl_sum)

        # -- Reset / Copy / Clear / Exit buttons --
        btn_reset_slot = QPushButton("×")
        btn_reset_slot.setFixedSize(24, 24)
        btn_reset_slot.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        btn_reset_slot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_reset_slot.setToolTip("Reset current slot settings to defaults")
        btn_reset_slot.clicked.connect(self._reset_current_slot)
        layout.addWidget(btn_reset_slot)

        btn_copy = QPushButton("⎘")
        btn_copy.setFixedSize(24, 24)
        btn_copy.setFont(QFont("Arial", 14))
        btn_copy.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_copy.setToolTip("Copy sums to clipboard (tab-delimited)")
        btn_copy.clicked.connect(self._copy_sums_clipboard)
        layout.addWidget(btn_copy)

        layout.addStretch(1)

        btn_exit = QPushButton("Exit")
        btn_exit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)

        return bar

    # ==================================================================
    # Slot management
    # ==================================================================

    def _populate_slot_combo(self):
        names = self._store.load_all_slot_names()
        self.cmb_custom.blockSignals(True)
        self.cmb_custom.clear()
        for i, name in enumerate(names):
            self.cmb_custom.addItem(f"{i+1}: {name}")
        self.cmb_custom.setCurrentIndex(self._current_slot - 1)
        self.cmb_custom.blockSignals(False)

    def _load_slot(self, slot: int):
        self._loading = True
        self._current_slot = slot
        data = self._store.load_slot(slot)

        # Window title
        self.setWindowTitle(f"CellCounter — {data['custom_name']}")

        # Slot combo
        self._populate_slot_combo()

        # Active counter count
        n = int(data.get("use_counters", 4))
        self._apply_counter_count(n)

        # Per-counter configs
        counter_cfgs = data.get("counters", [])
        for i, w in enumerate(self._counters):
            if i < len(counter_cfgs):
                w.apply_config(counter_cfgs[i])
            w.set_value(0.0)   # always start fresh

        # Sum alarm
        self._sum_alarm_value = int(data.get("sum_alarm_value", 100))
        self.lbl_sum_alarm.setText(str(self._sum_alarm_value))
        self.sum_progress.setMaximum(int(data.get("sum_alarm_value", 100)))

        self.cmb_sum_alarm.blockSignals(True)
        self.cmb_sum_alarm.setCurrentIndex(int(data.get("sum_alarm_index", 3)))
        self.cmb_sum_alarm.blockSignals(False)

        # Keyclick
        kc = bool(data.get("key_clicks", False))
        self.chk_sound.blockSignals(True)
        self.chk_sound.setChecked(kc)
        self.chk_sound.blockSignals(False)
        self._sound.set_click_enabled(kc)

        self._update_sum(cur_index=-1)
        self._loading = False

        # Start new log session
        self._logger.start_session(
            slot=slot,
            slot_name=data["custom_name"],
            counter_names=[self._counters[i].title() for i in range(n)],
            use_counters=n,
        )

    def _save_current_slot(self):
        if self._loading:
            return
        data = {
            "custom_name":     self._slot_name(self._current_slot),
            "use_counters":    self._use_counters,
            "sum_alarm_value": self._sum_alarm_value,
            "sum_alarm_index": self.cmb_sum_alarm.currentIndex(),
            "key_clicks":      self.chk_sound.isChecked(),
            "counters":        [w.get_config() for w in self._counters],
        }
        self._store.save_slot(self._current_slot, data)

    def _slot_name(self, slot: int) -> str:
        names = self._store.load_all_slot_names()
        idx = slot - 1
        if 0 <= idx < len(names):
            return names[idx]
        return f"Custom Settings {slot}"

    # ------------------------------------------------------------------
    # Counter count
    # ------------------------------------------------------------------

    def _apply_counter_count(self, n: int):
        self._use_counters = n
        for i, w in enumerate(self._counters):
            w.setVisible(i < n)

        # Update combobox without triggering _on_num_changed
        mapping = {4: 0, 8: 1, 12: 2, 16: 3}
        self.cmb_num.blockSignals(True)
        self.cmb_num.setCurrentIndex(mapping.get(n, 0))
        self.cmb_num.blockSignals(False)

        # Calculate exact height: menu bar + grid rows + bottom bar + margins
        QApplication.processEvents()
        visible_rows = (n + 3) // 4  # ceil(n / 4)
        # Get height of one counter widget
        row_h = self._counters[0].sizeHint().height()
        grid_spacing = self._grid.spacing()
        grid_h = visible_rows * row_h + max(0, visible_rows - 1) * grid_spacing

        menu_h = self.menuBar().sizeHint().height()
        bottom_h = self._bottom_bar.height()  # fixed at 34
        margins = 4 + 4  # top + bottom from root layout
        spacing = 4      # spacing between grid and bottom bar
        title_bar_h = self.frameGeometry().height() - self.geometry().height()
        if title_bar_h <= 0:
            title_bar_h = 31  # reasonable default

        total = title_bar_h + menu_h + margins + grid_h + spacing + bottom_h

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.resize(self.width(), total)
        self.setFixedHeight(total)

    # ==================================================================
    # Key handling  (local Qt focus)
    # ==================================================================

    def keyPressEvent(self, event: QKeyEvent):
        # Ignore auto-repeat
        if event.isAutoRepeat():
            return

        key = event.key()
        mods = event.modifiers()

        # R (any modifier) → reset all
        if key == Qt.Key.Key_R:
            self._clear_all()
            return

        for i in range(self._use_counters):
            w = self._counters[i]
            if w._input_open:
                continue
            if key == w.assigned_key:
                if mods & Qt.KeyboardModifier.ControlModifier:
                    w.reset_value()
                elif mods & Qt.KeyboardModifier.ShiftModifier:
                    w.decrement()
                else:
                    w.increment()
                return

        super().keyPressEvent(event)

    # ==================================================================
    # Sum calculation
    # ==================================================================

    def _update_sum(self, cur_index: int, action: int = 0):
        total = sum(
            self._counters[i].value
            for i in range(self._use_counters)
            if self._counters[i].chk_add.isChecked()
        )
        self.lbl_sum.setText(f"{int(total):,}")
        limit = self._sum_alarm_value
        self.sum_progress.setMaximum(limit)
        self.sum_progress.setValue(min(int(total), limit))

        # Sum alarm — only on increment hitting exact threshold
        if action == +1 and int(total) == limit:
            self._sound.play_alarm(self.cmb_sum_alarm.currentIndex())

        # Log a data row
        values = [self._counters[i].value for i in range(self._use_counters)]
        included = [self._counters[i].chk_add.isChecked() for i in range(self._use_counters)]
        self._logger.append_row(values, self._use_counters, included, cur_index)

    # ==================================================================
    # Slots connected from CounterWidget signals
    # ==================================================================

    def _on_value_changed(self, index: int, new_value: float, action: int):
        self._sound.play_click()
        self._update_sum(cur_index=index, action=action)
        self._save_current_slot()

    def _on_alarm_triggered(self, index: int, alarm_index: int):
        self._sound.play_alarm(alarm_index)

    # ==================================================================
    # Bottom-bar slots
    # ==================================================================

    def _on_num_changed(self, combo_index: int):
        n = (combo_index + 1) * 4
        self._apply_counter_count(n)
        self._update_sum(-1)
        self._save_current_slot()

    def _on_slot_changed(self, combo_index: int):
        if self._loading:
            return
        self._load_slot(combo_index + 1)

    def _on_keyclick_changed(self, state: int):
        self._sound.set_click_enabled(bool(state))
        self._save_current_slot()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "Reset All Counters",
            "Reset all counters to zero?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for w in self._counters:
                w.set_value(0.0)
            self._update_sum(-1)
            self._save_current_slot()
            # Restart log session
            slot_name = self._slot_name(self._current_slot)
            self._logger.start_session(
                slot=self._current_slot,
                slot_name=slot_name,
                counter_names=[self._counters[i].title() for i in range(self._use_counters)],
                use_counters=self._use_counters,
            )

    def _reset_current_slot(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            f"Reset all settings for slot {self._current_slot} to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from cellcounter.settings import _default_slot  # noqa: PLC0415
            self._store.save_slot(self._current_slot, _default_slot(self._current_slot))
            self._load_slot(self._current_slot)

    # ==================================================================
    # Context menus
    # ==================================================================

    def _sum_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Copy Sum to Clipboard", self._copy_sum_value)
        menu.exec(self.lbl_sum.mapToGlobal(pos))

    def _copy_sum_value(self):
        QApplication.clipboard().setText(self.lbl_sum.text().replace(",", ""))

    # ==================================================================
    # Format menu
    # ==================================================================

    def _rename_slot(self):
        current_name = self._slot_name(self._current_slot)
        name, ok = QInputDialog.getText(
            self, "Rename Settings Slot",
            f"Name for slot {self._current_slot}:", text=current_name,
        )
        if ok and name.strip():
            self._store.save_slot_name(self._current_slot, name.strip())
            self.setWindowTitle(f"CellCounter — {name.strip()}")
            self._populate_slot_combo()

    def _edit_sum_alarm(self):
        val, ok = QInputDialog.getInt(
            self, "...",
            "Sum alarm threshold:",
            self._sum_alarm_value, 1, 9_999_999,
        )
        if ok:
            self._sum_alarm_value = val
            self.lbl_sum_alarm.setText(str(val))
            self._save_current_slot()
            self._update_sum(-1)  # refresh progress bar

    # ==================================================================
    # File / clipboard operations
    # ==================================================================

    def _formatted_sums(self, sep: str = "\t", quote: bool = False) -> str:
        """Build header+data row for active counters + sum."""
        names = [self._counters[i].title() for i in range(self._use_counters)]
        values = [self._counters[i].value for i in range(self._use_counters)]
        total = sum(
            v for i, v in enumerate(values)
            if self._counters[i].chk_add.isChecked()
        )
        if quote:
            header = sep.join(f'"{n}"' for n in names) + sep + '"Sum"'
            data   = sep.join(str(int(v)) for v in values) + sep + str(int(total))
        else:
            header = sep.join(names) + sep + "Sum"
            data   = sep.join(str(int(v)) for v in values) + sep + str(int(total))
        return header + "\n" + data + "\n"

    def _save_tab(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sums (Excel format)", "", "Text files (*.txt)"
        )
        if path:
            Path(path).write_text(self._formatted_sums("\t"), encoding="utf-8")

    def _save_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sums as CSV", "", "CSV files (*.csv)"
        )
        if path:
            Path(path).write_text(self._formatted_sums(",", quote=True), encoding="utf-8")

    def _save_log(self):
        src = self._logger.log_path()
        if src is None or not src.exists():
            QMessageBox.information(self, "No Log", "No log data to save yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", "", "Log files (*.log);;Text files (*.txt)"
        )
        if path:
            shutil.copy2(src, path)

    def _copy_sums_clipboard(self):
        QApplication.clipboard().setText(self._formatted_sums("\t"))

    def _copy_log_clipboard(self):
        content = self._logger.read_log()
        if content:
            QApplication.clipboard().setText(content)
        else:
            QMessageBox.information(self, "No Log", "No log data to copy yet.")

    def _copy_form_bitmap(self):
        screen = QApplication.primaryScreen()
        if screen:
            pixmap = screen.grabWindow(int(self.winId()))
            QApplication.clipboard().setPixmap(pixmap)

    # ==================================================================
    # Help / About
    # ==================================================================

    def _open_help(self):
        from PyQt6.QtCore import QUrl  # noqa: PLC0415
        from PyQt6.QtGui import QDesktopServices  # noqa: PLC0415

        # Look for .chm next to executable first, then in VB6 source folder
        import sys as _sys  # noqa: PLC0415
        candidates = [
            Path(_sys.executable).parent / "cellcounter.chm",
            Path(__file__).parent.parent / "CellCounterVB6" / "cellcounter.chm",
        ]
        for chm in candidates:
            if chm.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(chm)))
                return
        QMessageBox.information(
            self, "Help",
            "Help file (cellcounter.chm) not found.\n"
            "Place cellcounter.chm next to the executable.",
        )

    def _show_about(self):
        from cellcounter.about_dialog import AboutDialog  # noqa: PLC0415
        dlg = AboutDialog(_APP_VERSION, self)
        dlg.exec()

    # ==================================================================
    # Close event
    # ==================================================================

    def closeEvent(self, event: QCloseEvent):
        self._save_current_slot()
        self._logger.close()   # deletes temp log (mirrors Form_Unload)
        super().closeEvent(event)
