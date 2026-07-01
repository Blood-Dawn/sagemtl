"""Automated release checklist runner for SageMTL."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


_CANONICAL_DOCS = ("README.md", "DEV.md", "ROADMAP.md", "AGENTS.md")


@dataclass(slots=True)
class ReleaseCheck:
    key: str
    description: str
    command: Sequence[str]
    required: bool = True


@dataclass(slots=True)
class ReleaseCheckResult:
    check: ReleaseCheck
    returncode: int
    duration_seconds: float
    output: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def build_release_checks(include_integration: bool = False) -> list[ReleaseCheck]:
    """Build the default release verification checklist."""
    python = sys.executable

    checks = [
        ReleaseCheck(
            key="docs",
            description="Canonical docs exist",
            command=[
                python,
                "-c",
                (
                    "from pathlib import Path; "
                    "required=('README.md','DEV.md','ROADMAP.md','AGENTS.md'); "
                    "missing=[p for p in required if not Path(p).exists()]; "
                    "print('Missing docs:', ', '.join(missing)) if missing else print('Docs present'); "
                    "raise SystemExit(1 if missing else 0)"
                ),
            ],
            required=True,
        ),
        ReleaseCheck(
            key="lint",
            description="Ruff lint",
            command=[
                python, "-m", "ruff", "check",
                "sagemtl", "sagemtl_desktop", "sagemtl_crawler", "sagemtl_manga_crawler",
                "scripts", "tests",
            ],
            required=True,
        ),
        ReleaseCheck(
            key="manga_licenses",
            description="LICENSES-MANGA.md present",
            command=[
                python, "-c",
                "from pathlib import Path; "
                "raise SystemExit(0 if Path('LICENSES-MANGA.md').exists() else 1)",
            ],
            required=True,
        ),
        ReleaseCheck(
            key="manga_lazy_imports",
            description="Manga module gains no heavy ML import (novel path stays light)",
            command=[
                python, "-c",
                (
                    "import sys; import sagemtl_desktop.core.manga.pipeline; "
                    "heavy=('torch','onnxruntime','paddle','paddleocr','transformers','cv2','manga_ocr','easyocr','huggingface_hub','numpy'); "
                    "leaked=[m for m in heavy if m in sys.modules]; "
                    "print('Heavy modules leaked:', leaked) if leaked else print('Manga lazy-import OK'); "
                    "raise SystemExit(1 if leaked else 0)"
                ),
            ],
            required=True,
        ),
        ReleaseCheck(
            key="tests_non_integration",
            description="Pytest non-integration suite",
            command=[python, "-m", "pytest", "-m", "not integration"],
            required=True,
        ),
        ReleaseCheck(
            key="imports",
            description="Import smoke check",
            command=[python, "-c", "import sagemtl, sagemtl_desktop, sagemtl_crawler, sagemtl_manga_crawler; print('Import smoke check passed')"],
            required=True,
        ),
    ]

    if include_integration:
        checks.append(
            ReleaseCheck(
                key="tests_integration",
                description="Desktop integration crawl test",
                command=[
                    python,
                    "-m",
                    "pytest",
                    "tests/desktop/test_lncrawl_integration.py",
                    "-m",
                    "integration",
                    "-v",
                ],
                required=False,
            )
        )

    return checks


def run_release_checks(
    checks: Sequence[ReleaseCheck],
    cwd: str | Path | None = None,
) -> list[ReleaseCheckResult]:
    """Run checks sequentially and return detailed results."""
    results: list[ReleaseCheckResult] = []
    for check in checks:
        start = time.perf_counter()
        process = subprocess.run(
            list(check.command),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
        )
        duration = time.perf_counter() - start
        output_parts = [process.stdout.strip(), process.stderr.strip()]
        output = "\n".join(part for part in output_parts if part)
        results.append(
            ReleaseCheckResult(
                check=check,
                returncode=process.returncode,
                duration_seconds=duration,
                output=output,
            )
        )
    return results


def render_release_summary(results: Sequence[ReleaseCheckResult], show_output: bool = False) -> str:
    """Render a human-friendly summary for CLI output."""
    lines = ["Release checklist results:"]
    for result in results:
        status = "PASS" if result.success else "FAIL"
        required = "required" if result.check.required else "optional"
        lines.append(
            f"[{status}] {result.check.key} ({required}) - {result.check.description} "
            f"({result.duration_seconds:.2f}s)"
        )
        if result.output and (show_output or not result.success):
            lines.append(result.output)

    required_failures = [item for item in results if item.check.required and not item.success]
    lines.append("")
    if required_failures:
        lines.append(f"Release checklist failed: {len(required_failures)} required check(s) failed.")
    else:
        lines.append("Release checklist passed.")

    return "\n".join(lines)


def run_release_checklist(
    include_integration: bool = False,
    show_output: bool = False,
    cwd: str | Path | None = None,
) -> int:
    """Build, run, and print the release checklist. Returns process exit code."""
    checks = build_release_checks(include_integration=include_integration)
    results = run_release_checks(checks, cwd=cwd)
    print(render_release_summary(results, show_output=show_output))

    required_failures = [item for item in results if item.check.required and not item.success]
    return 1 if required_failures else 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SageMTL release checklist automation")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Include optional integration test checks",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="Show command output for successful checks too",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return run_release_checklist(
        include_integration=args.integration,
        show_output=args.show_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
