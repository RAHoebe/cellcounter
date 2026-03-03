# cellcounter.spec — PyInstaller build spec
# Build with:  pyinstaller cellcounter.spec
#
# Produces:  dist/CellCounter.exe  (single-file executable)

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all WAV files from cellcounter/resources/
resources_src = os.path.join('cellcounter', 'resources')

# Gather ALL PyQt6 submodules, data files, and binaries
pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')
pynput_datas, pynput_binaries, pynput_hiddenimports = collect_all('pynput')

a = Analysis(
    ['cellcounter/__main__.py'],
    pathex=['.'],
    binaries=pyqt6_binaries + pynput_binaries,
    datas=[
        (resources_src, 'resources'),   # all WAVs bundled alongside exe
        ('version.txt', '.'),            # version file at bundle root
    ] + pyqt6_datas + pynput_datas,
    hiddenimports=[
        'platformdirs',
    ] + pyqt6_hiddenimports + pynput_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='CellCounter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowless app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cellcounter/resources/app.ico',
)
