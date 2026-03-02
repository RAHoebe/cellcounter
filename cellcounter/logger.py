"""
logger.py
Session data logger — tab-delimited, Excel-compatible.
Mirrors addDataLog() in frmCount.frm.

Log file: %LOCALAPPDATA%\\CellCounter\\cellcounterXXXXXX.log
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Sequence


class DataLogger:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._log_path: Path | None = None
        self._t0: float | None = None        # perf_counter at first data row
        self._session_started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_file(self) -> Path:
        if self._log_path is None:
            data_dir = self._data_dir
            data_dir.mkdir(parents=True, exist_ok=True)
            suffix = secrets.token_hex(3)   # 6 hex chars
            self._log_path = data_dir / f"cellcounter{suffix}.log"
        return self._log_path

    def close(self):
        """Delete the temp log on clean exit (mirrors Form_Unload)."""
        if self._log_path and self._log_path.exists():
            try:
                self._log_path.unlink()
            except OSError:
                pass
        self._log_path = None

    # ------------------------------------------------------------------
    # Public: start new session
    # ------------------------------------------------------------------

    def start_session(
        self,
        slot: int,
        slot_name: str,
        counter_names: list[str],
        use_counters: int,
    ):
        """
        Write header block.  Mirrors addDataLog(True).
        """
        path = self._ensure_file()
        self._t0 = None
        self._session_started = True
        now = datetime.now()
        date_str = now.strftime("%H:%M -- %d %B %Y")

        col_names = counter_names[:use_counters]
        headers = (
            ["Time (ms)"]
            + [f"{n} (sum)" for n in col_names]
            + ["Sum"]
            + [f"{n} (active)" for n in col_names]
            + ["Counter (nr)"]
        )

        try:
            with path.open("a", encoding="utf-8", newline="") as f:
                f.write("CellCounter Data Log File\n")
                f.write("\n")
                f.write(f"{date_str}\n")
                f.write(f"Custom Settings {slot}: {slot_name}\n")
                f.write("\n")
                f.write("\t".join(headers) + "\n")
        except OSError:
            pass  # silently skip if locked

    # ------------------------------------------------------------------
    # Public: append one data row
    # ------------------------------------------------------------------

    def append_row(
        self,
        values: Sequence[float],
        use_counters: int,
        included: Sequence[bool],
        cur_index: int,
    ):
        """
        Append one data row.  Mirrors addDataLog(False).
        values[0..use_counters-1] are the counter values; sum is computed here.
        included[i] is True if counter i is added to sum (chkAdd).
        cur_index is the 0-based counter that just changed (or -1 for bulk reset).
        """
        if not self._session_started:
            return

        now_t = time.perf_counter()

        # First data row: reset the clock
        if self._t0 is None:
            self._t0 = now_t

        elapsed_ms = round((now_t - self._t0) * 1000)

        counts = list(values[:use_counters])
        total = sum(v for i, v in enumerate(counts) if included[i])
        active_flags = [1 if included[i] else 0 for i in range(use_counters)]

        row = (
            [str(elapsed_ms)]
            + [self._fmt(v) for v in counts]
            + [self._fmt(total)]
            + [str(f) for f in active_flags]
            + [str(cur_index + 1) if cur_index >= 0 else "0"]
        )

        path = self._ensure_file()
        try:
            with path.open("a", encoding="utf-8", newline="") as f:
                f.write("\t".join(row) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Public: read log content for clipboard / save-as
    # ------------------------------------------------------------------

    def read_log(self) -> str:
        if self._log_path and self._log_path.exists():
            try:
                return self._log_path.read_text(encoding="utf-8")
            except OSError:
                return ""
        return ""

    def log_path(self) -> Path | None:
        return self._log_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(v: float) -> str:
        """Format counter value: integer if whole, else float."""
        if v == int(v):
            return str(int(v))
        return str(v)
