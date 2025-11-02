# Batch Translation

Batch translation jobs let you process entire corpora while reusing shared
configuration. The batch runner handles discovery, chunking, and retries so you
can focus on inputs and outputs.

## Running a Batch Job

```bash
sagemtl batch run \
  --input ./datasets/news/ \
  --output ./translated/news/ \
  --pattern "*.txt" \
  --resume
```

### Key Flags

- `--input PATH` – Directory or manifest file describing source documents.
- `--output PATH` – Destination directory for translated artifacts.
- `--pattern GLOB` – Optional glob filter when crawling directories.
- `--resume` – Continue a partially completed run without reprocessing files.

## Monitoring Progress

The CLI reports per-file progress and summarises throughput at the end of the
run. Combine with `--log-level debug` for detailed diagnostics.

## Integrations

- Use alongside the [Settings](settings.md) module to load project-specific
  translation parameters.
- Chain with shell tools (e.g., `find`, `parallel`) for bespoke scheduling.
- Export metrics to your observability stack by enabling the metrics plugin in
  the settings file.
