"""
counter_widget.py
QGroupBox representing one counter slot — mirrors Frame1(I) in frmCount.frm.

Signals emitted upward to the main window:
  alarm_triggered(index, alarm_index)
  value_changed(index, new_value, action)   action: +1/-1/0
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cellcounter.key_map import ALARM_NAMES, KEY_LIST


class CounterWidget(QGroupBox):
    """One counter panel — corresponds to Frame1(I) in the VB6 app."""

    alarm_triggered     = pyqtSignal(int, int)   # (counter_index, alarm_index)
    value_changed       = pyqtSignal(int, float, int)  # (counter_index, new_value, action)
    alarm_value_changed = pyqtSignal()             # emitted when user edits alarm value

    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(f"Counter {index + 1}", parent)
        self.index = index
        self.value: float = 0.0
        self._input_open = False  # guard while InputDialog is open

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 18, 6, 4)
        outer.setSpacing(4)

        # ── Row 1: large counter value display (full width) ──
        self.lbl_value = QLabel("0")
        self.lbl_value.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_value.setMinimumHeight(54)
        self.lbl_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lbl_value.setStyleSheet(
            "background: #FFFFFF; color: #000000; border: 1px solid #808080; padding: 2px 6px;"
        )
        self.lbl_value.setToolTip("Left-click to enter value manually\nRight-click for options")
        self.lbl_value.mousePressEvent = self._value_label_mouse  # type: ignore[assignment]
        outer.addWidget(self.lbl_value)

        # ── Row 2:  [−]  Alarm <spinbox> <progress> <checkbox>  [+] ──
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        self.btn_minus = QPushButton("−")
        self.btn_minus.setFont(QFont("Verdana", 18, QFont.Weight.Bold))
        self.btn_minus.setFixedSize(36, 36)
        self.btn_minus.setToolTip("Decrement  (Shift + key)")
        self.btn_minus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row2.addWidget(self.btn_minus)

        # Center group: Alarm label + threshold spinbox + progress bar
        center_col = QVBoxLayout()
        center_col.setSpacing(2)

        alarm_row = QHBoxLayout()
        alarm_row.setSpacing(3)
        alarm_lbl = QLabel("Alarm")
        alarm_lbl.setFont(QFont("Arial", 8))
        self._alarm_value: int = 100
        self.lbl_alarm_val = QLabel("100")
        self.lbl_alarm_val.setFixedWidth(55)
        self.lbl_alarm_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_alarm_val.setStyleSheet(
            "background: #FFE0E0; border: 1px solid #808080; padding: 1px 4px;"
        )
        self.lbl_alarm_val.setToolTip("Alarm threshold")

        self.btn_edit_alarm = QPushButton("...")
        self.btn_edit_alarm.setFixedSize(26, 22)
        self.btn_edit_alarm.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_edit_alarm.setToolTip("Edit alarm value")
        self.btn_edit_alarm.clicked.connect(self._set_alarm_dialog)

        self.chk_add = QCheckBox()
        self.chk_add.setChecked(True)
        self.chk_add.setToolTip("Include value in Counters Sum")
        self.chk_add.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        alarm_row.addWidget(alarm_lbl)
        alarm_row.addWidget(self.lbl_alarm_val)
        alarm_row.addWidget(self.btn_edit_alarm)
        alarm_row.addStretch(1)
        alarm_row.addWidget(self.chk_add)
        center_col.addLayout(alarm_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #808080; border-radius: 2px; background: #F0F0F0; }"
            "QProgressBar::chunk { background: #FF0000; border-radius: 1px; }"
        )
        center_col.addWidget(self.progress)

        row2.addLayout(center_col, stretch=1)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setFont(QFont("Verdana", 18, QFont.Weight.Bold))
        self.btn_plus.setFixedSize(36, 36)
        self.btn_plus.setToolTip("Increment  (key alone)")
        self.btn_plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row2.addWidget(self.btn_plus)

        outer.addLayout(row2)

        # ── Row 3:  Key combo | reset(×) | Alarm-sound combo ──
        row3 = QHBoxLayout()
        row3.setSpacing(4)

        self.cmb_key = QComboBox()
        self.cmb_key.setStyleSheet("QComboBox { background: #D0FFFF; }")
        self.cmb_key.setToolTip("Assigned key")
        self.cmb_key.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for label, _ in KEY_LIST:
            self.cmb_key.addItem(label)

        self.btn_reset = QPushButton("×")
        self.btn_reset.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_reset.setFixedSize(24, 24)
        self.btn_reset.setToolTip("Reset to 0  (Ctrl + key)")
        self.btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.cmb_alarm = QComboBox()
        self.cmb_alarm.setToolTip("Alarm sound")
        self.cmb_alarm.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for name in ALARM_NAMES:
            self.cmb_alarm.addItem(name)

        row3.addWidget(self.cmb_key, stretch=2)
        row3.addWidget(self.btn_reset)
        row3.addWidget(self.cmb_alarm, stretch=2)
        outer.addLayout(row3)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_plus.clicked.connect(self.increment)
        self.btn_minus.clicked.connect(self.decrement)
        self.btn_reset.clicked.connect(self.reset_value)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Set Font Color…",       self._set_fore_color)
        menu.addAction("Set Background Color…", self._set_back_color)
        menu.addAction("Set Alarm Value…",      self._set_alarm_dialog)
        menu.addAction("Rename Counter…",       self._rename_counter)
        menu.addSeparator()
        menu.addAction("Copy Value to Clipboard", self._copy_value)
        menu.exec(event.globalPosition().toPoint())

    def _set_fore_color(self):
        current = QColor(self._get_fore_color())
        color = QColorDialog.getColor(current, self, "Select Font Color")
        if color.isValid():
            self._apply_colors(fore=color.name())

    def _set_back_color(self):
        current = QColor(self._get_back_color())
        color = QColorDialog.getColor(current, self, "Select Background Color")
        if color.isValid():
            self._apply_colors(back=color.name())

    def _get_fore_color(self) -> str:
        # Parse from stylesheet
        ss = self.lbl_value.styleSheet()
        for part in ss.split(";"):
            part = part.strip()
            if part.startswith("color:"):
                return part.split(":", 1)[1].strip()
        return "#000000"

    def _get_back_color(self) -> str:
        ss = self.lbl_value.styleSheet()
        for part in ss.split(";"):
            part = part.strip()
            if part.startswith("background:"):
                return part.split(":", 1)[1].strip()
        return "#FFFFFF"

    def _apply_colors(self, fore: str | None = None, back: str | None = None):
        current_fore = self._get_fore_color()
        current_back = self._get_back_color()
        f = fore or current_fore
        b = back or current_back
        self.lbl_value.setStyleSheet(
            f"background: {b}; color: {f}; border: 1px solid #808080; padding: 2px 6px;"
        )

    def _set_alarm_dialog(self):
        val, ok = QInputDialog.getInt(
            self, "...",
            f"Alarm threshold for {self.title()}:",
            self._alarm_value, 1, 9_999_999,
        )
        if ok:
            self._alarm_value = val
            self.lbl_alarm_val.setText(str(val))
            self.progress.setMaximum(val)
            self._update_display(-1000)  # refresh progress bar
            self.alarm_value_changed.emit()  # trigger save

    def _rename_counter(self):
        name, ok = QInputDialog.getText(
            self, "Rename Counter",
            "Counter name:",
            text=self.title(),
        )
        if ok and name.strip():
            self.setTitle(name.strip())

    def _copy_value(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._format_value(self.value))

    # ------------------------------------------------------------------
    # Mouse on value label
    # ------------------------------------------------------------------

    def _value_label_mouse(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._manual_entry()
        elif event.button() == Qt.MouseButton.RightButton:
            self.contextMenuEvent(event)

    def _manual_entry(self):
        """InputDialog to manually set the counter value."""
        self._input_open = True
        val, ok = QInputDialog.getDouble(
            self, f"Set {self.title()}",
            "Enter value:",
            self.value, 0, 9_999_999, 0,
        )
        self._input_open = False
        if ok:
            self.value = float(val)
            self._update_display(-1000)  # -1000 = display-only, no alarm check
            self.value_changed.emit(self.index, self.value, 0)

    # ------------------------------------------------------------------
    # Counter operations
    # ------------------------------------------------------------------

    def increment(self):
        self.value += 1
        self._update_display(+1)
        self.value_changed.emit(self.index, self.value, +1)
        self._check_alarm(+1)

    def decrement(self):
        if self.value > 0:
            self.value -= 1
            self._update_display(-1)
            self.value_changed.emit(self.index, self.value, -1)

    def reset_value(self):
        self.value = 0.0
        self._update_display(0)
        self.value_changed.emit(self.index, 0.0, 0)

    def set_value(self, v: float):
        """Set value programmatically (e.g., bulk clear). No alarm fired."""
        self.value = float(v)
        self._update_display(-1000)

    def set_compact_mode(self, mode: int):
        """Show/hide controls for compact view mode.
        
        Args:
            mode: 0=full, 1=compact, 2=ultra-compact
        """
        is_compact = mode > 0  # Any compact mode hides controls
        is_ultra = mode == 2   # Ultra-compact also reduces sizes
        
        # Keep visible: counter name (QGroupBox title) and lbl_value
        # Hide when compact: buttons, alarms, config row
        self.btn_plus.setVisible(not is_compact)
        self.btn_minus.setVisible(not is_compact)
        self.btn_reset.setVisible(not is_compact)
        self.btn_edit_alarm.setVisible(not is_compact)
        self.lbl_alarm_val.setVisible(not is_compact)
        self.chk_add.setVisible(not is_compact)
        self.progress.setVisible(not is_compact)
        self.cmb_key.setVisible(not is_compact)
        self.cmb_alarm.setVisible(not is_compact)
        
        # Also hide the "Alarm" label - find it in the layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.layout():
                # This is row2 (QHBoxLayout)
                for j in range(item.layout().count()):
                    sub_item = item.layout().itemAt(j)
                    if sub_item and sub_item.layout():
                        # This is center_col (QVBoxLayout)
                        for k in range(sub_item.layout().count()):
                            alarm_item = sub_item.layout().itemAt(k)
                            if alarm_item and alarm_item.layout():
                                # This is alarm_row
                                for m in range(alarm_item.layout().count()):
                                    label_item = alarm_item.layout().itemAt(m)
                                    if label_item and label_item.widget():
                                        widget = label_item.widget()
                                        if isinstance(widget, QLabel) and widget.text() == "Alarm":
                                            widget.setVisible(not is_compact)
        
        # Adjust font size and spacing for ultra-compact mode
        if is_ultra:
            # Reduce font size for value label
            self.lbl_value.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            self.lbl_value.setMinimumHeight(40)
            # Reduce outer margins
            self.layout().setContentsMargins(4, 14, 4, 2)
        else:
            # Restore normal sizes
            if mode == 0:  # Only restore in full mode, not compact
                self.lbl_value.setFont(QFont("Arial", 36, QFont.Weight.Bold))
                self.lbl_value.setMinimumHeight(54)
                self.layout().setContentsMargins(6, 18, 6, 4)
            else:  # Compact but not ultra
                # Keep compact size but not ultra-reduced
                self.lbl_value.setFont(QFont("Arial", 36, QFont.Weight.Bold))
                self.lbl_value.setMinimumHeight(54)
                self.layout().setContentsMargins(6, 18, 6, 4)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _update_display(self, action: int):
        self.lbl_value.setText(self._format_value(self.value))
        limit = self._alarm_value
        bar_val = min(int(self.value), limit)
        self.progress.setMaximum(limit)
        self.progress.setValue(bar_val)

    @staticmethod
    def _format_value(v: float) -> str:
        """Format with commas.  e.g. 1234.0 → '1,234'"""
        i = int(v)
        return f"{i:,}"

    def _check_alarm(self, action: int):
        """Fire alarm signal when value exactly hits threshold on increment."""
        if action == +1 and int(self.value) == self._alarm_value:
            self.alarm_triggered.emit(self.index, self.cmb_alarm.currentIndex())

    def _on_alarm_changed(self, val: int):
        self.progress.setMaximum(val)

    # ------------------------------------------------------------------
    # Config getters / setters (used by main_window for save/load)
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        return {
            "name":         self.title(),
            "alarm_value":  self._alarm_value,
            "fore_color":   self._get_fore_color(),
            "back_color":   self._get_back_color(),
            "add_to_sum":   self.chk_add.isChecked(),
            "key_index":    self.cmb_key.currentIndex(),
            "alarm_index":  self.cmb_alarm.currentIndex(),
        }

    def apply_config(self, cfg: dict):
        self.setTitle(cfg.get("name", self.title()))
        alarm_val = int(cfg.get("alarm_value", 1000))
        self._alarm_value = alarm_val
        self.lbl_alarm_val.setText(str(alarm_val))
        self.progress.setMaximum(alarm_val)
        fore = cfg.get("fore_color", "#000000")
        back = cfg.get("back_color", "#FFFFFF")
        self._apply_colors(fore=fore, back=back)
        self.chk_add.setChecked(bool(cfg.get("add_to_sum", True)))
        ki = int(cfg.get("key_index", self.index if self.index < len(KEY_LIST) else 0))
        self.cmb_key.setCurrentIndex(min(ki, self.cmb_key.count() - 1))
        ai = int(cfg.get("alarm_index", 0))
        self.cmb_alarm.setCurrentIndex(min(ai, self.cmb_alarm.count() - 1))

    @property
    def assigned_key(self) -> int:
        """Return the Qt.Key constant for the currently selected key."""
        idx = self.cmb_key.currentIndex()
        if 0 <= idx < len(KEY_LIST):
            return KEY_LIST[idx][1]
        return -1
