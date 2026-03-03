"""
sound.py
Sound playback.
Uses winsound (Windows built-in) for zero-dependency async WAV playback.
Falls back silently on non-Windows platforms.

WAV files live in cellcounter/resources/ and are bundled via PyInstaller.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cellcounter.key_map import ALARM_NAMES

# ---------------------------------------------------------------------------
# Resolve the resources directory (works in dev and after PyInstaller bundle)
# ---------------------------------------------------------------------------

def _resources_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'resources'
    return Path(__file__).parent / 'resources'


# ---------------------------------------------------------------------------
# Generate a short click WAV in memory (8kHz, mono, 8-bit, ~15ms pulse)
# ---------------------------------------------------------------------------

import struct as _struct
import math as _math

def _generate_click_wav() -> bytes:
    """Create a tiny WAV with a 15 ms decaying click at 8000 Hz, mono, 8-bit."""
    sample_rate = 8000
    duration_ms = 15
    n_samples = sample_rate * duration_ms // 1000  # 120 samples
    freq = 1000.0  # Hz
    samples = bytearray(n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        envelope = 1.0 - (i / n_samples)  # linear decay
        val = int(128 + 80 * envelope * _math.sin(2 * _math.pi * freq * t))
        samples[i] = max(0, min(255, val))
    # Build a minimal WAV
    data_size = n_samples
    fmt_chunk = _struct.pack('<4sIHHIIHH',
        b'fmt ', 16, 1, 1, sample_rate, sample_rate, 1, 8)
    data_chunk = _struct.pack('<4sI', b'data', data_size) + bytes(samples)
    riff_size = 4 + len(fmt_chunk) + len(data_chunk)
    return _struct.pack('<4sI4s', b'RIFF', riff_size, b'WAVE') + fmt_chunk + data_chunk

_CLICK_BYTES = _generate_click_wav()


def _write_click_wav(path: Path):
    path.write_bytes(_CLICK_BYTES)


# ---------------------------------------------------------------------------
# Platform-safe winsound wrapper
# ---------------------------------------------------------------------------

if sys.platform == 'win32':
    import winsound as _winsound

    def _play_bytes(data: bytes):
        flags = _winsound.SND_MEMORY | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT
        try:
            _winsound.PlaySound(data, flags)
        except Exception:
            pass

    def _play_file_async(path: str):
        flags = _winsound.SND_FILENAME | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT
        try:
            _winsound.PlaySound(path, flags)
        except Exception:
            pass
else:
    def _play_bytes(data: bytes): pass
    def _play_file_async(path: str): pass


# ---------------------------------------------------------------------------
# SoundPlayer
# ---------------------------------------------------------------------------

class SoundPlayer:
    def __init__(self):
        self._click_enabled: bool = False
        self._alarm_paths: list = []
        self._click_wav: Path | None = None
        self._loaded = False

    def ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        res = _resources_dir()
        res.mkdir(parents=True, exist_ok=True)
        click_path = res / 'click.wav'
        if not click_path.exists():
            _write_click_wav(click_path)
        self._click_wav = click_path
        self._alarm_paths = []
        for name in ALARM_NAMES:
            wav = res / f'{name.lower()}.wav'
            self._alarm_paths.append(str(wav) if wav.exists() else None)

    def set_click_enabled(self, enabled: bool):
        self._click_enabled = enabled

    def play_click(self):
        if self._click_enabled and self._click_wav and self._click_wav.exists():
            _play_file_async(str(self._click_wav))

    def play_alarm(self, alarm_index: int):
        if not self._loaded:
            return
        if 0 <= alarm_index < len(self._alarm_paths):
            path = self._alarm_paths[alarm_index]
            if path:
                _play_file_async(path)
