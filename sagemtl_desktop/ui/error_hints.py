"""Helpers for turning raw errors into actionable recovery hints."""

from __future__ import annotations


def get_error_recovery_hints(error_message: str, context: str = "") -> list[str]:
    """Return ordered recovery hints for a UI error surface."""
    raw = (error_message or "").strip()
    text = raw.lower()
    ctx = (context or "").lower()

    hints: list[str] = []

    if "translation model not found" in text or "missing translation model" in text:
        hints.extend(
            [
                "Install the required Argos language pair before retrying translation.",
                "Use Translation > Translation Backend to switch to an available backend.",
            ]
        )

    if "argos" in text and ("install" in text or "not installed" in text):
        hints.append("Install Argos Translate with: pip install argostranslate")

    if "googletrans" in text and ("install" in text or "unavailable" in text):
        hints.append("Install googletrans backend with: pip install googletrans==4.0.0rc1")

    if "lightnovel-crawler" in text or "lncrawl" in text:
        hints.append("Install or update lightnovel-crawler, then restart SageMTL.")

    if "timeout" in text or "timed out" in text:
        hints.extend(
            [
                "Increase request delay/retries in crawl options and retry.",
                "Retry from a stable network connection.",
            ]
        )

    if "connection" in text or "dns" in text or "network" in text:
        hints.append("Verify internet connectivity and site availability, then retry.")

    if "permission" in text or "access denied" in text:
        hints.append("Choose a writable output directory and verify file permissions.")

    if "no chapters" in text:
        hints.extend(
            [
                "Try a different source URL or open crawl options and lower restrictions.",
                "Use Batch Crawl for multiple mirrors and compare results.",
            ]
        )

    if ctx in {"search", "crawl_search"}:
        hints.append("Try a more specific novel title or paste a direct chapter/novel URL.")

    if ctx in {"crawl", "crawl_discovery", "crawl_download"}:
        hints.append("Review site-specific crawl profile (delay, retries, robots override) and retry.")

    if ctx in {"processing", "translation"}:
        hints.append("Switch translation backend or reduce chunk size, then rerun the job.")

    if ctx in {"export"}:
        hints.append("Ensure export directory exists and has free disk space.")

    if not hints:
        hints.append("Retry the action once; if it keeps failing, open job details for traceback.")

    # Preserve ordering while removing duplicates.
    unique_hints: list[str] = []
    seen = set()
    for hint in hints:
        if hint in seen:
            continue
        seen.add(hint)
        unique_hints.append(hint)
    return unique_hints


def build_actionable_error_text(error_message: str, context: str = "", max_hints: int = 3) -> str:
    """Format an error with a concise recovery checklist for message boxes."""
    details = (error_message or "Unknown error").strip()
    hints = get_error_recovery_hints(details, context=context)
    if not hints:
        return details

    rendered_hints = "\n".join(f"- {hint}" for hint in hints[:max_hints])
    return f"{details}\n\nSuggested next steps:\n{rendered_hints}"
