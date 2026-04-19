# Installing Warp

## Prerequisites

- Python 3.11+
- pip or uv

## Install

```bash
# From source (development install)
git clone https://github.com/jamesmtuck/warp.git
cd warp
pip install -e ".[dev]"
```

For OpenAI support:
```bash
pip install -e ".[openai]"
```

## Initialize Configuration

```bash
warp config init
```

This creates:
- `~/.config/warp/config.toml` — your configuration
- `~/.local/share/warp/warp.db` — your command history database

## Shell Integration

### Zsh

Add to `~/.zshrc`:

```zsh
# Warp integration
if command -v warp &>/dev/null; then
    WARP_SHELL_DIR="$(python3 -c 'import warp.shell; import os; print(os.path.dirname(warp.shell.__file__))')"
    source "${WARP_SHELL_DIR}/zsh_integration.sh"
fi
```

### Bash

Add to `~/.bashrc`:

```bash
# Warp integration
if command -v warp &>/dev/null; then
    WARP_SHELL_DIR="$(python3 -c 'import warp.shell; import os; print(os.path.dirname(warp.shell.__file__))')"
    source "${WARP_SHELL_DIR}/bash_integration.sh"
fi
```

## Import Existing History

```bash
warp import-history          # auto-detects bash or zsh
warp import-history --shell zsh
warp import-history --shell bash --file ~/.bash_history
```

## Key Bindings (after shell integration)

| Key | Action |
|-----|--------|
| `Ctrl-F` | Interactive history search |
| `Alt-A` | AI command generation |

## Verify Installation

```bash
warp doctor
```
