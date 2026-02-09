# AGENTS.md

This file is the operating guide for any AI agent working in this repository.

## 1. Mission

Maintain and extend SageMTL as a reliable desktop-first workflow for:

- Crawling web novels.
- Translating text locally.
- Managing glossary-driven cleanup.
- Exporting high-quality output.

Your goal is to ship correct, testable improvements without introducing drift between docs, code, and tests.

## 2. Ground truth and scope

Primary active surfaces:

- Desktop app: `sagemtl_desktop/`
- Shared CLI/core helpers: `sagemtl/`
- Secondary crawler engine: `sagemtl_crawler/`

Canonical docs to keep updated:

- `README.md`
- `DEV.md`
- `ROADMAP.md`
- `AGENTS.md`

Do not create new standalone markdown docs unless explicitly requested.

## 3. Current architecture facts

- The desktop app is orchestrated by `sagemtl_desktop/ui/main_window.py`.
- Job execution uses `sagemtl_desktop/core/job_manager.py`.
- Translation uses Argos through `sagemtl_desktop/core/translator.py`.
- Search, URL classification, and UI crawl execution route through `LightNovelCrawlerWrapper`.
- `sagemtl_desktop/core/crawl_service.py` owns chapter discovery/download strategy selection.
- `GenericNovelCrawler` is now used as a fallback path behind the wrapper/service.
- `sagemtl_crawler/` exists but is not the main desktop runtime path.

Important: Never assume old docs are correct; validate behavior in code before making claims.

## 4. High-risk areas

Treat these as change-sensitive:

- `sagemtl_desktop/ui/main_window.py` (large, multi-responsibility).
- Crawler flow boundary between wrapper/service and generic fallback paths.
- Glossary duplication (`glossary.py` and `glossary_manager.py`).
- Packaging spec (`pyinstaller-desktop.spec`) and bundled resources.
- CLI command surface where modules may be missing at runtime.

## 5. Required workflow for agents

1. Inspect first.
- Run targeted discovery (`rg --files`, `rg -n`, focused file reads).
- Validate assumptions from implementation, not from old prose.

2. Plan before large edits.
- Identify affected modules.
- Call out correctness risks and test impact.

3. Implement minimally.
- Prefer small, isolated changes.
- Avoid broad refactors unless requested or required for correctness.

4. Validate changes.
- Run relevant tests.
- Run lint for touched files or full lint if feasible.

5. Update docs and roadmap.
- If behavior changes, update `README.md`, `DEV.md`, or `ROADMAP.md` in the same change.
- Mark roadmap items complete only when implemented and validated.

## 6. Commands agents should know

Environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-desktop.txt
```

Run app:

```powershell
python -m sagemtl_desktop.main
```

Tests:

```powershell
python -m pytest -m "not integration"
python -m pytest tests/desktop/test_lncrawl_integration.py -m integration -v
```

Lint:

```powershell
python -m ruff check sagemtl sagemtl_desktop sagemtl_crawler tests
```

## 7. Engineering standards

- Keep changes ASCII unless file already requires Unicode.
- Prefer explicit error handling over broad silent exceptions.
- Avoid adding duplicate abstractions when one already exists.
- Keep UI logic thin; move business logic into `core/` modules when possible.
- Add tests for new behavior or bug fixes.

## 8. Documentation standards

- `README.md`: user-facing setup and usage.
- `DEV.md`: technical reference, architecture, validation commands, optimization audit.
- `ROADMAP.md`: single source of planning truth and status tracking.
- `AGENTS.md`: agent execution guide.

When you complete roadmap work:

- Update checkbox status.
- Add a short note if scope changed.
- Do not leave ambiguous status.

## 9. Decision rules for agents

If a request conflicts with current architecture:

- Prefer correctness and explicitness over preserving outdated behavior.
- If removing obsolete paths, ensure tests/docs are updated in the same task.

If a request is broad (example: "optimize codebase"):

- Produce prioritized findings with file-level references.
- Implement low-risk wins if asked.
- Convert findings into concrete roadmap tasks.

## 10. Pre-handoff checklist

Before finalizing work, verify:

- Code compiles/imports for touched modules.
- Relevant tests pass.
- Lint findings for touched files are not regressed.
- Canonical docs reflect the new behavior.
- `ROADMAP.md` status is accurate.

If any validation step is skipped, state exactly what was not run and why.
