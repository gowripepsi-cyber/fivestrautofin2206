# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter

# Find customtkinter path
ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['app.py'],
    pathex=['.', 'reusable_master'],
    binaries=[],
    datas=[
        (ctk_path, 'customtkinter/'),
        ('nagudi_auto.db', '.'), # Include initial DB if exists
        ('reusable_master', 'reusable_master'), # Include internal package
    ],
    hiddenimports=['tkcalendar', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageTk'],
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
    [],
    exclude_binaries=True,
    name='Nagudi Auto Finance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Nagudi Auto Finance',
)
