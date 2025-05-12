# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# datas = [('C:\\Users\\zengz\\Desktop\\Code\\multi-withdrawl\\app.ico', '.'), ('C:\\Users\\zengz\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\candlelite\\SETTINGS.config', 'candlelite')]
# Use relative paths for project assets where possible
datas = [('app.ico', '.'), ('twitter.png', '.')] 
# Add other external dependencies if needed, e.g.:
# datas += [('path/to/external/dependency.config', 'dependency_dir')]
datas += collect_data_files('PyQt6')


a = Analysis(
    # Use relative path for entry script
    ['main_qt.py'], 
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MultiWithdrawalHelper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\zengz\\Desktop\\Code\\multi-withdrawl\\app.ico'],
)
