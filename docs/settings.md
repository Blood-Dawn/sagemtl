# Settings Reference

SageMTL reads configuration from a layered settings system that merges defaults,
project files, and command-line overrides.

## Configuration Locations

1. **Default package settings** baked into `sagemtl.settings`.
2. **Project settings file** (e.g., `config/sagemtl.yml`).
3. **User overrides** supplied via the `--config` flag or environment variables.

## File Format

Settings files are YAML documents with nested sections such as:

```yaml
model:
  name: gpt-4
  endpoint: https://api.openai.com/v1/chat/completions
batch:
  max_workers: 4
  retry_limit: 3
logging:
  level: info
```

## Environment Variables

Map uppercase keys to nested paths using `__` as a separator. For example:

```bash
export SAGEMTL_MODEL__NAME="local-mtl"
```

## Inspecting Effective Settings

Use the CLI to view merged values:

```bash
sagemtl settings show --format yaml
```

Combine with `--config` to inspect alternative configuration files.
