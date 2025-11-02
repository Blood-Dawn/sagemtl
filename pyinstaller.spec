# -*- mode: python ; coding: utf-8 -*-
"""Template PyInstaller spec for packaging the SageMTL CLI/TUI binary.

Adjust the paths, datas, and hiddenimports arrays as the project evolves. This
file is intentionally conservative so contributors can iterate from a known base.
"""

from pathlib import Path

project_root = Path(__file__).resolve().parent

block_cipher = None

a = Analysis(
    ['sagemtl/__main__.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Example: ("sagemtl/assets", "sagemtl/assets"),
    ],
    hiddenimports=[
        # Add optional runtime dependencies here.
    ],
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
    [],
    name='sagemtl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sagemtl',
)
