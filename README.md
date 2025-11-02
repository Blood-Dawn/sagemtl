# sagemtl

Blood-Dawn — starter repo for the SageMTL toolchain (docs, crawler, ML).

## Goals

- MTL pipeline experiments (crawler + cleaning + models)
- Reproducible envs (.venv-ml, .venv-doc, .venv-crawl)

## Quickstart

```bash
# create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# install sagemtl in editable mode with its tooling extras
pip install -e .[cli]

# explore the command line help and kick off a translation run
sagemtl --help
sagemtl translate --input sample.txt --output translated.txt
```

> **Note**
> Use `python -m pip install -e .[all]` if you intend to experiment with the crawler,
> cleaning, or model training components in a single environment.

## Features at a Glance

- **Interactive translation** via both CLI and TUI front-ends with shared translation logic.
- **Batch processing** pipeline for translating multiple files or directories at once.
- **Configurable settings** to tune model, caching, and resource usage per environment.

Refer to the [documentation](docs/index.md) for deeper dives into each workflow.

## Interface Preview Placeholders

Real screenshots will land soon—use the notes below as a guide when producing them.

### TUI Preview

> _Screenshot coming soon: capture the terminal UI showcasing live translation feedback._

### CLI Preview

> _Screenshot coming soon: highlight `sagemtl translate` arguments and sample output._

## Batch and Translate Workflows

The translation stack powers both interactive and automated flows:

- Use the **Translate** command group to run quick experiments from the CLI or TUI.
- Spin up the **Batch** runner to process entire corpora with consistent settings.

Each workflow shares configuration defaults and can be tailored through the
project-wide settings file documented under [`docs/settings.md`](docs/settings.md).
