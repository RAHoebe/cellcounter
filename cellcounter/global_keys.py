"""
global_keys.py
System-wide keyboard listener using *pynput*.

Runs a background thread that captures every key press/release regardless
of which window has focus.  Modifier state (Ctrl, Shift) is tracked
internally so that the emitted Qt signal carries the correct modifier mask.

Signal:  key_pressed(int qt_key, int qt_modifiers)
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, pyqtSignal

try:
    from pynput import keyboard
    _HAS_PYNPUT = True
except ImportError:
    keyboard = None  # type: ignore[assignment]
    _HAS_PYNPUT = False


# ── Key-translation tables ────────────────────────────────────────────

def _build_maps() -> tuple[dict, dict]:
    """Build pynput → Qt.Key lookup dicts (called once at import time)."""
    if not _HAS_PYNPUT:
        return {}, {}

    special: dict = {
        keyboard.Key.left:  Qt.Key.Key_Left,
        keyboard.Key.right: Qt.Key.Key_Right,
        keyboard.Key.down:  Qt.Key.Key_Down,
        keyboard.Key.up:    Qt.Key.Key_Up,
        keyboard.Key.f1:    Qt.Key.Key_F1,
        keyboard.Key.f2:    Qt.Key.Key_F2,
        keyboard.Key.f3:    Qt.Key.Key_F3,
        keyboard.Key.f4:    Qt.Key.Key_F4,
        keyboard.Key.f5:    Qt.Key.Key_F5,
        keyboard.Key.f6:    Qt.Key.Key_F6,
        keyboard.Key.f7:    Qt.Key.Key_F7,
        keyboard.Key.f8:    Qt.Key.Key_F8,
        keyboard.Key.f9:    Qt.Key.Key_F9,
        keyboard.Key.f10:   Qt.Key.Key_F10,
        keyboard.Key.f11:   Qt.Key.Key_F11,
        keyboard.Key.f12:   Qt.Key.Key_F12,
    }

    char: dict[str, int] = {}
    for c in "abcdefghijklmnopqrstuvwxyz":
        char[c] = getattr(Qt.Key, f"Key_{c.upper()}")
    for d in "0123456789":
        char[d] = getattr(Qt.Key, f"Key_{d}")

    return special, char


_SPECIAL_MAP, _CHAR_MAP = _build_maps()

# Modifier key sets (pynput uses separate enums for left/right variants)
_CTRL_KEYS: set = set()
_SHIFT_KEYS: set = set()
if _HAS_PYNPUT:
    for _name in ("ctrl", "ctrl_l", "ctrl_r"):
        if hasattr(keyboard.Key, _name):
            _CTRL_KEYS.add(getattr(keyboard.Key, _name))
    for _name in ("shift", "shift_l", "shift_r"):
        if hasattr(keyboard.Key, _name):
            _SHIFT_KEYS.add(getattr(keyboard.Key, _name))


# ── Qt signal bridge ──────────────────────────────────────────────────

class _KeySignalBridge(QObject):
    """Transfers events from the pynput thread to the Qt main thread."""
    key_pressed = pyqtSignal(int, int)  # (qt_key_value, qt_modifiers_mask)


# ── Public class ──────────────────────────────────────────────────────

class GlobalKeyListener:
    """Manages a system-wide keyboard hook.

    Usage::

        gk = GlobalKeyListener()
        gk.key_pressed.connect(my_slot)
        gk.start()     # begin capturing
        gk.stop()      # stop capturing
    """

    def __init__(self) -> None:
        self._bridge = _KeySignalBridge()
        self._listener = None  # type: ignore[assignment]
        self._active = False
        self._ctrl = False
        self._shift = False

    # -- public API -------------------------------------------------------

    @property
    def key_pressed(self):
        """pyqtSignal(int, int) — connect to receive (qt_key, qt_modifiers)."""
        return self._bridge.key_pressed

    @staticmethod
    def available() -> bool:
        """Return True if pynput is installed."""
        return _HAS_PYNPUT

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if not _HAS_PYNPUT or self._active:
            return
        self._ctrl = self._shift = False
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        self._active = True

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._active = False
        self._ctrl = self._shift = False

    # -- pynput callbacks (background thread) -----------------------------

    def _on_press(self, key) -> None:  # noqa: ANN001
        # Track modifier state
        if key in _CTRL_KEYS:
            self._ctrl = True
            return
        if key in _SHIFT_KEYS:
            self._shift = True
            return

        qt_key = self._translate(key)
        if qt_key is None:
            return

        mods = 0
        if self._ctrl:
            mods |= int(Qt.KeyboardModifier.ControlModifier)
        if self._shift:
            mods |= int(Qt.KeyboardModifier.ShiftModifier)

        self._bridge.key_pressed.emit(qt_key, mods)

    def _on_release(self, key) -> None:  # noqa: ANN001
        if key in _CTRL_KEYS:
            self._ctrl = False
        elif key in _SHIFT_KEYS:
            self._shift = False

    # -- key translation --------------------------------------------------

    @staticmethod
    def _translate(key) -> int | None:  # noqa: ANN001
        """Convert a pynput key to a Qt.Key int, or None if unmapped."""
        # Special keys (arrows, F-keys)
        if hasattr(key, "name"):
            return _SPECIAL_MAP.get(key)

        # Character keys
        if hasattr(key, "char") and key.char is not None:
            return _CHAR_MAP.get(key.char.lower())

        # Virtual-key fallback (numpad digits when NumLock is off, etc.)
        if hasattr(key, "vk") and key.vk is not None:
            vk = key.vk
            # Numpad 0–9: VK_NUMPAD0 (0x60) – VK_NUMPAD9 (0x69)
            if 0x60 <= vk <= 0x69:
                return _CHAR_MAP.get(str(vk - 0x60))
            # Arrows: VK_LEFT (0x25) – VK_DOWN (0x28)
            _VK_ARROWS = {
                0x25: int(Qt.Key.Key_Left),
                0x26: int(Qt.Key.Key_Up),
                0x27: int(Qt.Key.Key_Right),
                0x28: int(Qt.Key.Key_Down),
            }
            if vk in _VK_ARROWS:
                return _VK_ARROWS[vk]

        return None
