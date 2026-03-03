# CellCounter

A lightweight, keyboard-driven cell counting application for laboratory use.  
Designed for microscopy workflows where hands stay on the keyboard and eyes stay on the specimen.

Originally written in **Visual Basic 6** (2008), now fully rewritten in **Python 3 + PyQt6**.

---

## Features

- **Up to 16 counters** arranged in a 4-column grid (choose 4 / 8 / 12 / 16)
- **52 assignable keyboard keys** — arrow keys and A–Z, 0–9, plus extras
- **One-key counting**: press the assigned key to increment
  - `Key` = **+1** &ensp;|&ensp; `Shift+Key` = **−1** &ensp;|&ensp; `Ctrl+Key` = **Reset to 0**
  - `R` = **Reset all counters** (with confirmation)
- **Per-counter alarms** — set a target value, pick a sound (8 built-in alarm WAVs)
- **Sum alarm** — fires when the total across all counters hits a threshold
- **Local / Global key mode** — choose whether keys are captured only when the
  window has focus (*Local*) or system-wide (*Global*, via `pynput`)
- **Keyclick sound** — audible feedback on every keypress (toggle on/off)
- **8 settings slots** — save and recall complete configurations (names, keys, colours, alarms)
- **Customisable counter names and colours** via right-click context menus
- **Progress bar** showing the proportion of sum alarm reached
- **Session logging** — tab-delimited log with millisecond-precision timestamps
- **Export**: Save as CSV, TAB-delimited, or raw log; copy sums / log / form to clipboard

---

## Screenshot

![CellCounter screenshot](docs/Screenshot%202026-03-02%20161143.png)

---

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Python | ≥ 3.10 | |
| PyQt6 | ≥ 6.6 | |
| platformdirs | ≥ 4.0 | |
| pynput | ≥ 1.7 | Required for Global key mode |

Platform: **Windows** (uses `winsound` for audio playback and `msinfo32` for System Info).

---

## Installation

### From source

```bash
# Clone the repository
git clone https://github.com/<your-username>/CellCounter.git
cd CellCounter

# (Optional) create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python -m cellcounter
```

---

## Building a standalone executable

The project includes a [PyInstaller](https://pyinstaller.org/) spec file that produces a **single-file `.exe`** — no Python installation required on the target machine.

### Prerequisites

```bash
pip install pyinstaller
```

### Build

```bash
pyinstaller cellcounter.spec
```

The executable will be created at:

```
dist/CellCounter.exe
```

### What the spec does

| Setting | Value |
|---|---|
| Mode | **One-file** (`EXE` with all binaries/data embedded) |
| Console | **Hidden** (windowed GUI app) |
| Icon | `cellcounter/resources/app.ico` (multi-resolution: 16–256 px) |
| Bundled data | All WAV sounds from `cellcounter/resources/`, `version.txt` |

---

## Project structure

```
CellCounter/
├── cellcounter/
│   ├── __init__.py          # Package marker
│   ├── __main__.py          # Entry point, icon loading, bright palette
│   ├── main_window.py       # Main window (QMainWindow), menus, keyboard capture
│   ├── counter_widget.py    # Individual counter widget (QGroupBox)
│   ├── key_map.py           # 52-key mapping list & alarm sound names
│   ├── settings.py          # JSON settings persistence (8 slots)
│   ├── logger.py            # Tab-delimited session logger
│   ├── sound.py             # Sound playback (winsound) & click generation
│   ├── global_keys.py       # System-wide keyboard listener (pynput)
│   ├── about_dialog.py      # About dialog
│   └── resources/           # Bundled assets
│       ├── app.ico          # Application icon (16–256 px)
│       ├── click.wav        # Keyclick sound
│       ├── bleep.wav        # Alarm sounds …
│       ├── boing.wav
│       ├── bomb.wav
│       ├── chord.wav
│       ├── drum.wav
│       ├── explode.wav
│       ├── fanfare.wav
│       └── gong.wav
├── version.txt              # Version string (e.g. v1.0.0)
├── requirements.txt         # Python dependencies
├── cellcounter.spec          # PyInstaller build spec
├── .gitignore
└── README.md
```

---

## Settings storage

User settings are stored as JSON at:

```
%LOCALAPPDATA%\CellCounter\settings.json
```

Each of the **8 slots** stores:

- Counter names, key assignments, colours, alarm values & sounds
- Number of active counters (4 / 8 / 12 / 16)
- Sum alarm value & sound
- Keyclick on/off

A **global** setting (outside slots) stores:

- Key mode preference (Local / Global)

---

## Versioning

The version string lives in `version.txt` at the project root.  
It is read at runtime by both the application and the About dialog.  
When building with PyInstaller, the file is bundled into the executable.

---

## History

| Era | Technology | Notes |
|---|---|---|
| 2008 | Visual Basic 6 | Original desktop application |
| 2026 | Python 3 + PyQt6 | Complete rewrite, same UX |

---

## License

Copyright &copy; 2008–2026 **Ron Hoebe**  
Amsterdam UMC, The Netherlands

Contact: [R.A.Hoebe@amsterdamumc.nl](mailto:R.A.Hoebe@amsterdamumc.nl)
