"""Tests for release checklist automation helpers."""

from types import SimpleNamespace

from sagemtl.release_check import (
    ReleaseCheck,
    ReleaseCheckResult,
    build_release_checks,
    render_release_summary,
    run_release_checks,
)


def test_build_release_checks_default_includes_core_checks():
    checks = build_release_checks(include_integration=False)
    keys = [check.key for check in checks]

    assert "docs" in keys
    assert "lint" in keys
    assert "tests_non_integration" in keys
    assert "imports" in keys
    assert "tests_integration" not in keys


def test_run_release_checks_collects_output(monkeypatch):
    calls = []

    def fake_run(command, cwd=None, capture_output=True, text=True):  # noqa: ANN001
        calls.append((command, cwd, capture_output, text))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("sagemtl.release_check.subprocess.run", fake_run)

    checks = [
        ReleaseCheck(
            key="lint",
            description="Lint",
            command=["python", "-m", "ruff", "check"],
            required=True,
        )
    ]

    results = run_release_checks(checks, cwd=".")

    assert len(results) == 1
    assert results[0].success is True
    assert "ok" in results[0].output
    assert calls


def test_render_release_summary_reports_failures():
    check = ReleaseCheck(
        key="tests",
        description="Tests",
        command=["python", "-m", "pytest"],
        required=True,
    )
    result = ReleaseCheckResult(
        check=check,
        returncode=1,
        duration_seconds=1.2,
        output="failed",
    )

    summary = render_release_summary([result], show_output=False)

    assert "[FAIL] tests" in summary
    assert "failed" in summary
    assert "required check(s) failed" in summary
