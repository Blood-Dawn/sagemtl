# sagemtl
Blood-Dawn — starter repo for the SageMTL toolchain (docs, crawler, ML).

## Goals
- MTL pipeline experiments (crawler + cleaning + models)
- Reproducible envs (.venv-ml, .venv-doc, .venv-crawl)

## Quality gates

Install the development dependencies and set up the pre-commit hooks to run
the shared formatting and linting workflow:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pre-commit install
```

The hook stack runs Ruff (import sorting and E401 checks), Black, and Pytest.
You can trigger the entire suite locally with:

```bash
pre-commit run --all-files
```

Or run the test gate directly via:

```bash
pytest
```

