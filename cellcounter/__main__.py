"""
__main__.py — entry point.
Run with:  python -m cellcounter
"""

import ctypes
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QImageReader, QPalette, QColor, QPixmap
from PyQt6.QtWidgets import QApplication

from cellcounter.main_window import CellCounterWindow

_ICON_PATH = Path(__file__).parent / "resources" / "app.ico"


def _load_ico_icon(path: str) -> QIcon:
    """Load an .ico file using explicit format (PyQt6 auto-detect fails).

    Reads every image in the ICO, scales up to common sizes if missing,
    and returns a QIcon with all available sizes.
    """
    reader = QImageReader(path, b"ICO")
    icon = QIcon()
    images = []
    for i in range(reader.imageCount()):
        reader.jumpToImage(i)
        img = reader.read()
        if not img.isNull():
            images.append(img)
            icon.addPixmap(QPixmap.fromImage(img))

    # Ensure we have 32×32 and 48×48 for Windows taskbar / title bar.
    if images:
        largest = max(images, key=lambda im: im.width())
        for sz in (32, 48):
            if not any(im.width() == sz for im in images):
                scaled = largest.scaled(
                    sz, sz,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon.addPixmap(QPixmap.fromImage(scaled))
    return icon


def _apply_bright_palette(app: QApplication):
    """Force a standard bright / light palette (like classic Windows)."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base,            QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text,            QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button,          QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def main():
    # Tell Windows this is its own app (not python.exe) so our icon shows
    # in the taskbar instead of the Python logo.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "RonHoebe.CellCounter.1"
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("CellCounter")
    app.setOrganizationName("RonHoebe")

    # Read version from version.txt
    from cellcounter.main_window import _APP_VERSION
    app.setApplicationVersion(_APP_VERSION)

    _apply_bright_palette(app)

    if _ICON_PATH.exists():
        icon = _load_ico_icon(str(_ICON_PATH))
        if not icon.isNull():
            app.setWindowIcon(icon)

    window = CellCounterWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
