"""Install the manga module dependencies and warm the model cache.

This is the on-demand installer for SageMTL's manga features. It is never run at
app launch; the desktop/novel path has zero manga dependencies. Run it once
before using Manga mode:

    python scripts/setup_manga.py                 # install deps + warm cache
    python scripts/setup_manga.py --no-download   # install deps only
    python scripts/setup_manga.py --no-install    # warm cache only
    python scripts/setup_manga.py --models detector ocr_ja   # subset of models

Only permissive (Apache-2.0 / MIT) weights are downloaded (see the model
registry). Heavy ML imports stay inside the manga package and are loaded lazily.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Default models warmed on first setup: the offline pipeline that needs no key.
DEFAULT_WARM_MODELS = ("detector", "segmenter", "ocr_ja", "inpaint_lama")

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements-manga.txt"

# Running "python scripts/setup_manga.py" puts scripts/ on sys.path, not the repo
# root, so the sagemtl* packages are not importable. Put the repo root first.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def install_requirements() -> int:
    """Install requirements-manga.txt with the current interpreter's pip."""

    if not REQUIREMENTS.exists():
        print(f"ERROR: {REQUIREMENTS} not found.", file=sys.stderr)
        return 1
    print(f"Installing manga dependencies from {REQUIREMENTS} ...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    return subprocess.call(cmd)


def warm_cache(model_keys: list[str]) -> int:
    """Download the requested models into ~/.sagemtl/models via the registry."""

    try:
        from sagemtl_desktop.core.manga import model_registry
    except Exception as exc:  # pragma: no cover - defensive import guard
        print(f"ERROR: could not import the manga model registry: {exc}", file=sys.stderr)
        return 1

    device = model_registry.select_device("auto")
    print(f"Selected device: {device}")
    print(f"Model cache: {model_registry.models_cache_dir()}")

    failures = 0
    for key in model_keys:
        try:
            spec = model_registry.get_spec(key)
        except KeyError as exc:
            print(f"  SKIP {key}: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(f"  Downloading {key} ({spec.repo_id}, {spec.license}) ...")
        try:
            path = model_registry.ensure(key)
            print(f"    -> {path}")
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"    FAILED {key}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set up the SageMTL manga module.")
    parser.add_argument("--no-install", action="store_true", help="Skip pip install.")
    parser.add_argument("--no-download", action="store_true", help="Skip model cache warmup.")
    parser.add_argument(
        "--models",
        nargs="*",
        default=list(DEFAULT_WARM_MODELS),
        help="Model keys to warm (default: offline pipeline).",
    )
    args = parser.parse_args(argv)

    rc = 0
    if not args.no_install:
        rc = install_requirements()
        if rc != 0:
            print("Dependency install failed; skipping model warmup.", file=sys.stderr)
            return rc

    if not args.no_download:
        rc = warm_cache(args.models)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
