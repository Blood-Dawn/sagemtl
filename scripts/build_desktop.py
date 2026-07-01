"""Build a SageMTL desktop distribution with PyInstaller.

    python scripts/build_desktop.py            # novel-focused build (small)
    python scripts/build_desktop.py --manga    # full manga-enabled build (large)
    python scripts/build_desktop.py --manga --zip   # also zip dist/SageMTL

The novel build uses ``pyinstaller-desktop.spec`` (excludes the heavy manga ML
stack; manga deps install on demand from source). The manga build uses
``pyinstaller-manga.spec`` and bundles torch/paddle/transformers/onnxruntime/
opencv/manga-ocr + the crawler + fonts, so the whole app works from the frozen
build (model weights still download on first use). The manga build is several GB
and likely exceeds a GitHub release asset (2 GB per file) -- host it elsewhere.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the SageMTL desktop app.")
    parser.add_argument("--manga", action="store_true", help="Full manga-enabled build (large).")
    parser.add_argument("--zip", action="store_true", help="Zip dist/SageMTL after building.")
    args = parser.parse_args(argv)

    spec = "pyinstaller-manga.spec" if args.manga else "pyinstaller-desktop.spec"
    spec_path = REPO_ROOT / spec
    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found", file=sys.stderr)
        return 1

    print(f"Building with {spec} ...")
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm"]
    rc = subprocess.call(cmd, cwd=str(REPO_ROOT))
    if rc != 0:
        print("PyInstaller build failed.", file=sys.stderr)
        return rc

    dist = REPO_ROOT / "dist" / "SageMTL"
    print(f"Build complete: {dist}")
    if dist.exists():
        size_mb = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"Distribution size: {size_mb:.0f} MB")

    if args.zip and dist.exists():
        archive = REPO_ROOT / "dist" / "SageMTL-windows"
        print("Zipping ...")
        shutil.make_archive(str(archive), "zip", root_dir=str(dist.parent), base_dir="SageMTL")
        print(f"Archive: {archive}.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
