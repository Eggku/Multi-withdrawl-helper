# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_qt.py'],
    pathex=[],
    binaries=[],
    datas=[('app.ico', '.'), ('README_CONFIG.txt', 'README_CONFIG.txt')],
    hiddenimports=['pandas', 'PyQt6', 'binance', 'eth_utils', 'base58'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='币安提币助手',
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
    icon=['app.ico'],
)
