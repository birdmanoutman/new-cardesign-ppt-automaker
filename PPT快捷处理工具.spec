# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\dell\\Desktop\\share\\Syncdisk\\SLowBurn\\new-cardesign-ppt-automaker\\main.py'],
    pathex=[],
    binaries=[('C:\\Users\\dell\\Desktop\\share\\Syncdisk\\SLowBurn\\new-cardesign-ppt-automaker\\venv/Lib/site-packages/PyQt6/Qt6/bin/*', 'PyQt6/Qt6/bin')],
    datas=[('C:\\Users\\dell\\Desktop\\share\\Syncdisk\\SLowBurn\\new-cardesign-ppt-automaker\\src', 'src')],
    hiddenimports=['win32com.client', 'PIL', 'pptx', 'sqlite3'],
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
    name='PPT快捷处理工具',
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
)
