# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\zengz\\Desktop\\Code\\multi-withdrawl\\main_qt.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\zengz\\Desktop\\Code\\multi-withdrawl\\app.ico', '.'), ('C:\\Users\\zengz\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\candlelite\\SETTINGS.config', 'candlelite')],
    hiddenimports=['PyQt6.sip', 'PyQt6.QtNetwork', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtSvg', 'pandas', 'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype', 'numpy', 'openpyxl', 'requests', 'dateutil', 'six', 'binance', 'okx', 'eth_utils', 'eth_abi', 'base58', 'decimal', 'configparser', 'shutil', 'csv'],
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
