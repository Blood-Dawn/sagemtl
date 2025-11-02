# sagemtl
Pipeline: crawl -> clean -> translate.

## Development workflow

Set up the shared tooling before committing:

```bash
pip install -e .[dev]
pre-commit install
```

Run the quality checks locally:

```bash
pre-commit run --all-files
pytest
```
