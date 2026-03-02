"""
key_map.py
Ordered list of (label, Qt.Key) pairs that can be assigned to counters.
Mirrors the 52-key list from FillKeyCodes() / GetKeyName() in mdTimer.bas.
"""

from PyQt6.QtCore import Qt

# Each entry: (display_label, Qt.Key constant)
KEY_LIST: list[tuple[str, int]] = [
    ("LEFT ARROW",  Qt.Key.Key_Left),
    ("RIGHT ARROW", Qt.Key.Key_Right),
    ("DOWN ARROW",  Qt.Key.Key_Down),
    ("UP ARROW",    Qt.Key.Key_Up),
    # A–Z
    ("A", Qt.Key.Key_A),
    ("B", Qt.Key.Key_B),
    ("C", Qt.Key.Key_C),
    ("D", Qt.Key.Key_D),
    ("E", Qt.Key.Key_E),
    ("F", Qt.Key.Key_F),
    ("G", Qt.Key.Key_G),
    ("H", Qt.Key.Key_H),
    ("I", Qt.Key.Key_I),
    ("J", Qt.Key.Key_J),
    ("K", Qt.Key.Key_K),
    ("L", Qt.Key.Key_L),
    ("M", Qt.Key.Key_M),
    ("N", Qt.Key.Key_N),
    ("O", Qt.Key.Key_O),
    ("P", Qt.Key.Key_P),
    ("Q", Qt.Key.Key_Q),
    ("R", Qt.Key.Key_R),
    ("S", Qt.Key.Key_S),
    ("T", Qt.Key.Key_T),
    ("U", Qt.Key.Key_U),
    ("V", Qt.Key.Key_V),
    ("W", Qt.Key.Key_W),
    ("X", Qt.Key.Key_X),
    ("Y", Qt.Key.Key_Y),
    ("Z", Qt.Key.Key_Z),
    # Numpad 0–9
    ("NUMPAD 0", Qt.Key.Key_0),
    ("NUMPAD 1", Qt.Key.Key_1),
    ("NUMPAD 2", Qt.Key.Key_2),
    ("NUMPAD 3", Qt.Key.Key_3),
    ("NUMPAD 4", Qt.Key.Key_4),
    ("NUMPAD 5", Qt.Key.Key_5),
    ("NUMPAD 6", Qt.Key.Key_6),
    ("NUMPAD 7", Qt.Key.Key_7),
    ("NUMPAD 8", Qt.Key.Key_8),
    ("NUMPAD 9", Qt.Key.Key_9),
    # F1–F12
    ("F1",  Qt.Key.Key_F1),
    ("F2",  Qt.Key.Key_F2),
    ("F3",  Qt.Key.Key_F3),
    ("F4",  Qt.Key.Key_F4),
    ("F5",  Qt.Key.Key_F5),
    ("F6",  Qt.Key.Key_F6),
    ("F7",  Qt.Key.Key_F7),
    ("F8",  Qt.Key.Key_F8),
    ("F9",  Qt.Key.Key_F9),
    ("F10", Qt.Key.Key_F10),
    ("F11", Qt.Key.Key_F11),
    ("F12", Qt.Key.Key_F12),
]

# Alarm sound names (index matches cmbAlarm ListIndex in VB6)
ALARM_NAMES: list[str] = [
    "Bleep",    # 0
    "Boing",    # 1
    "Bomb",     # 2
    "Chord",    # 3
    "Explode",  # 4
    "Fanfare",  # 5
    "Drum",     # 6
    "Gong",     # 7
]

# Default alarm sound index per counter (0-based), mirrors InitSub smart defaults
# Counter0=Bleep, Counter1=Boing, Counter2=Chord, Counter3=Gong,
# Counter4=Fanfare, Counter5..=Bomb
DEFAULT_ALARM_INDEX: list[int] = [0, 1, 3, 7, 5, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]

# Default key index per counter (0-based index into KEY_LIST)
# Counter0=LEFT(0), Counter1=RIGHT(1), Counter2=DOWN(2), Counter3=UP(3),
# Counter4..N=index 4, 5, 6, …
DEFAULT_KEY_INDEX: list[int] = [0, 1, 2, 3] + list(range(4, 16))
