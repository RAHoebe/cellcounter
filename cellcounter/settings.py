"""
settings.py
Persistent settings storage using a single JSON file.
Path: %LOCALAPPDATA%\\CellCounter\\settings.json  (via platformdirs)

Structure:
{
  "slots": {
    "1": { <slot_data> },
    ...
    "8": { <slot_data> }
  }
}

slot_data keys:
  custom_name       str
  use_counters      int  (4 / 8 / 12 / 16)
  sum_alarm_value   int
  sum_alarm_index   int
  key_clicks        bool
  counters: list[16] of {
    name, alarm_value, fore_color, back_color, add_to_sum, key_index, alarm_index
  }
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

try:
    from platformdirs import user_data_dir
    _DATA_DIR = Path(user_data_dir("CellCounter", "RonHoebe"))
except ImportError:
    _DATA_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "CellCounter"

SETTINGS_FILE = _DATA_DIR / "settings.json"

NUM_SLOTS = 8
NUM_COUNTERS = 16


def _default_counter(index: int) -> dict:
    """Mirrors VB6 InitSub defaults for a single counter."""
    from cellcounter.key_map import DEFAULT_ALARM_INDEX, DEFAULT_KEY_INDEX
    return {
        "name": f"Counter {index + 1}",
        "alarm_value": 1000,
        "fore_color": "#000000",      # black text
        "back_color": "#FFFFFF",      # white background
        "add_to_sum": True,
        "key_index": DEFAULT_KEY_INDEX[index],
        "alarm_index": DEFAULT_ALARM_INDEX[index],
    }


def _default_slot(slot_num: int) -> dict:
    return {
        "custom_name": f"Custom Settings {slot_num}",
        "use_counters": 4,
        "sum_alarm_value": 100,
        "sum_alarm_index": 3,   # Chord
        "key_clicks": False,
        "counters": [_default_counter(i) for i in range(NUM_COUNTERS)],
    }


class SettingsStore:
    def __init__(self):
        self._data: dict = {}
        self._load_file()

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _load_file(self):
        if SETTINGS_FILE.exists():
            try:
                with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = raw.get("slots", {})
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def _save_file(self):
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump({"slots": self._data}, f, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_slot(self, slot: int) -> dict:
        """Return a complete slot dict (with defaults filled in)."""
        key = str(slot)
        stored = self._data.get(key, {})
        result = _default_slot(slot)
        # Deep-merge stored over defaults
        for k, v in stored.items():
            if k == "counters" and isinstance(v, list):
                for i, c in enumerate(v[:NUM_COUNTERS]):
                    if isinstance(c, dict):
                        result["counters"][i].update(c)
            else:
                result[k] = v
        return result

    def save_slot(self, slot: int, data: dict):
        """Persist one slot."""
        self._data[str(slot)] = deepcopy(data)
        self._save_file()

    def load_all_slot_names(self) -> list[str]:
        """Return list of 8 custom names (indexed 0–7 = slots 1–8)."""
        names = []
        for s in range(1, NUM_SLOTS + 1):
            slot_data = self._data.get(str(s), {})
            names.append(slot_data.get("custom_name", f"Custom Settings {s}"))
        return names

    def save_slot_name(self, slot: int, name: str):
        key = str(slot)
        if key not in self._data:
            self._data[key] = _default_slot(slot)
        self._data[key]["custom_name"] = name
        self._save_file()

    def data_dir(self) -> Path:
        return _DATA_DIR
