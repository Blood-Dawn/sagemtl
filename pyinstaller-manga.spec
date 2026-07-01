# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: F821
"""
PyInstaller spec for the FULL manga-enabled SageMTL desktop build.

Bundles the heavy ML stack (torch, paddle, transformers, onnxruntime, opencv,
manga-ocr) plus the crawler, fonts, and cloud SDKs, so novel translation AND the
whole manga pipeline (detect -> OCR -> translate -> inpaint -> typeset), the
Studio editor, crawling, and CBZ/PDF export all work from the frozen app. Model
WEIGHTS still download on first use into ~/.sagemtl/models/ (they are not bundled).

Build with:  pyinstaller pyinstaller-manga.spec --noconfirm
Result:      dist/SageMTL/ (one-folder distribution; several GB)

Note: this is a large, heavy build. torch/paddle are the fragile parts; if a
package's collection fails it is skipped with a printed warning rather than
aborting the whole spec.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    copy_metadata,
)

is_windows = sys.platform.startswith("win")
block_cipher = None

datas = []
binaries = []
hiddenimports = []


def _bundle(package):
    try:
        d, b, h = collect_all(package)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
        print(f"[manga-spec] bundled {package}: {len(d)} data, {len(b)} bin, {len(h)} hidden")
    except Exception as exc:  # keep going if one package can't be collected
        print(f"[manga-spec] WARNING: could not bundle {package}: {exc}")


# Heavy ML + manga stack (best-effort per package).
for _pkg in (
    "torch", "torchgen",
    "transformers", "tokenizers", "safetensors", "sentencepiece",
    "huggingface_hub", "hf_xet",
    "onnxruntime",
    "cv2",
    "numpy",
    "PIL",
    "shapely",
    "scipy", "sympy", "networkx",
    "manga_ocr", "jaconv", "fugashi", "unidic_lite",
    "paddle", "paddleocr", "paddlex",
    "pandas",
    "argostranslate", "ctranslate2",
    "anthropic", "openai",
    "httpx", "bs4", "lxml", "ebooklib", "pythonjsonlogger",
):
    _bundle(_pkg)

# Package metadata some libraries read at runtime (version lookups, entry points).
for _meta in (
    "torch", "transformers", "tokenizers", "huggingface-hub", "numpy", "tqdm",
    "regex", "filelock", "packaging", "safetensors", "pyyaml", "manga-ocr",
    "paddleocr", "paddlepaddle", "onnxruntime", "opencv-python-headless",
    "argostranslate", "sentencepiece",
):
    try:
        datas += copy_metadata(_meta)
    except Exception:
        pass

# The application's own packages (make sure lazy/dynamic imports are found).
for _pkg in ("sagemtl", "sagemtl_desktop", "sagemtl_crawler", "sagemtl_manga_crawler"):
    try:
        hiddenimports += collect_submodules(_pkg)
    except Exception as exc:
        print(f"[manga-spec] WARNING: submodules {_pkg}: {exc}")

# Bundled OFL fonts for the manga typesetter/Studio.
_fonts = Path("sagemtl_desktop/core/manga/fonts")
if _fonts.exists():
    datas.append((str(_fonts), "sagemtl_desktop/core/manga/fonts"))

# Bundled crawler source index files.
_sources = Path("sagemtl_manga_crawler/sources")
if _sources.exists():
    datas.append((str(_sources), "sagemtl_manga_crawler/sources"))

# App resources (icons, etc.). main.py resolves these via Path(__file__).parent,
# so they must land next to the package (sagemtl_desktop/resources), not top-level.
_resources = Path("sagemtl_desktop/resources")
if _resources.exists():
    datas.append((str(_resources), "sagemtl_desktop/resources"))

# Optional Argos language packs (bundled if the user installed any).
try:
    import argostranslate

    _argos_pkgs = Path(argostranslate.__file__).parent / "packages"
    if _argos_pkgs.exists():
        datas.append((str(_argos_pkgs), "argostranslate/packages"))
except Exception:
    pass

hiddenimports += [
    "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
]

windows_icon = Path("sagemtl_desktop/resources/icon.ico")
icon_path = str(windows_icon) if is_windows and windows_icon.exists() else None

a = Analysis(
    ["sagemtl_desktop/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "PyQt5", "PyQt6"],
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
    name="SageMTL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX + torch/onnxruntime DLLs are a bad mix; keep it off.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SageMTL",
)
