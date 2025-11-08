# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SageMTL Desktop Application.

Build with: pyinstaller pyinstaller-desktop.spec

This will create a one-folder distribution in dist/SageMTL/
"""

import os
import sys
from pathlib import Path

# Determine if we're building on Windows
is_windows = sys.platform.startswith('win')

block_cipher = None

# Get argostranslate package location for bundling models
try:
    import argostranslate
    argos_path = Path(argostranslate.__file__).parent
    argos_packages_path = argos_path / 'packages'
except ImportError:
    argos_path = None
    argos_packages_path = None

# Data files to include
datas = []

# Include Argos Translate models if available
if argos_packages_path and argos_packages_path.exists():
    datas.append((str(argos_packages_path), 'argostranslate/packages'))

# Include resources directory
resources_dir = Path('sagemtl_desktop/resources')
if resources_dir.exists():
    datas.append((str(resources_dir), 'resources'))

a = Analysis(
    ['sagemtl_desktop/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'argostranslate',
        'argostranslate.package',
        'argostranslate.translate',
        'argostranslate.apis',
        'argostranslate.utils',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SageMTL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='sagemtl_desktop/resources/icons/app.ico' if is_windows else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SageMTL',
)

# Note: To bundle Argos Translate language packs, you must install them first:
#
# >>> import argostranslate.package
# >>> argostranslate.package.update_package_index()
# >>> available_packages = argostranslate.package.get_available_packages()
# >>>
# >>> # Install Chinese -> English
# >>> zh_en = [pkg for pkg in available_packages if pkg.from_code == 'zh' and pkg.to_code == 'en'][0]
# >>> download_path = zh_en.download()
# >>> argostranslate.package.install_from_path(download_path)
# >>>
# >>> # Install Japanese -> English
# >>> ja_en = [pkg for pkg in available_packages if pkg.from_code == 'ja' and pkg.to_code == 'en'][0]
# >>> download_path = ja_en.download()
# >>> argostranslate.package.install_from_path(download_path)
# >>>
# >>> # Install Korean -> English
# >>> ko_en = [pkg for pkg in available_packages if pkg.from_code == 'ko' and pkg.to_code == 'en'][0]
# >>> download_path = ko_en.download()
# >>> argostranslate.package.install_from_path(download_path)
#
# After installing the packages, they will be automatically bundled when you build with PyInstaller.
