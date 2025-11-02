# Terminal User Interface (TUI)

The SageMTL TUI provides a live translation playground for quickly iterating on
prompting and configuration choices.

## Launching the TUI

```bash
sagemtl tui
```

The command detects your terminal size and adapts layout accordingly. Use the
`--config` flag to point to a custom settings file if required.

## Key Areas

- **Source Panel** – Paste or type text to translate; supports multiline editing.
- **Target Panel** – Displays the translated output with streaming updates.
- **Status Bar** – Shows active model, latency metrics, and token counts.

## Keyboard Shortcuts

| Action | Shortcut |
| --- | --- |
| Trigger translation | `Ctrl+Enter` |
| Clear buffers | `Ctrl+L` |
| Toggle settings drawer | `Ctrl+,` |
| Exit TUI | `Ctrl+C` |

## Tips

- Enable verbose logging with `--log-level debug` for troubleshooting.
- Pair the TUI with a local model server by updating the `model.endpoint` setting.
- Capture a screenshot once layout stabilizes to replace the placeholder in the README.
