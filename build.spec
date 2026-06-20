import os
import customtkinter
import matplotlib

block_cipher = None

ctk_path = os.path.dirname(customtkinter.__file__)
mpl_data = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, "customtkinter"),
        (mpl_data, "matplotlib/mpl-data"),
    ],
    hiddenimports=[
        "customtkinter",
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "psutil",
        "wmi",
        "win32api",
        "win32con",
        "pywintypes",
    ],
    hookspath=[],
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
    [],
    name="SysMonitor",
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
