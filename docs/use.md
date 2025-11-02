# Use SageMTL

This guide walks you through installing dependencies, configuring credentials, and
running your first translation jobs.

## Installation

1. Ensure Python 3.10+ is available on your system.
2. Create a virtual environment and activate it.
3. Install SageMTL and optional extras:

```bash
pip install -e .[cli]
```

Add the `crawl` or `ml` extras if you intend to operate those pipelines inside the
same environment.

## First Translation

1. Prepare a source text file (`sample.txt`).
2. Invoke the CLI translation command:

```bash
sagemtl translate --input sample.txt --output translated.txt
```

3. Review the translated output and adjust parameters as needed.

## Choosing an Interface

- **TUI**: Focused on interactive experimentation and rapid validation.
- **CLI**: Script-friendly interface that pairs nicely with shell pipelines.
- **Batch**: High-throughput translation for corpora or scheduled jobs.

Continue to the dedicated pages linked above for deeper instructions on each path.
