# Command Line Interface (CLI)

The CLI is ideal for scripted workflows and integration with shell pipelines.
All commands are exposed through the `sagemtl` entry point installed with the
package.

## Global Options

Run `sagemtl --help` to see available subcommands and global flags. Common
options include:

- `--config PATH` – Use a specific settings file.
- `--log-level {info,debug}` – Control log verbosity.
- `--profile` – Output profiling statistics for performance analysis.

## Translate Command

```bash
sagemtl translate --input input.txt --output output.txt \
  --model gpt-4 --batch-size 8
```

Arguments:

- `--input` accepts a file path or `-` for stdin.
- `--output` writes to a file or stdout.
- `--model` selects a configured translation backend.
- `--batch-size` controls the chunking strategy for larger files.

## Additional Subcommands

- `sagemtl tui` – Launch the interactive terminal interface.
- `sagemtl settings show` – Inspect the effective configuration.
- `sagemtl batch run` – Trigger a batch translation job (see [Batch](batch.md)).

Combine CLI invocations with `cron`, `make`, or CI pipelines to automate
translation tasks end to end.
