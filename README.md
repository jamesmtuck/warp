# warp

A local-first AI-powered terminal assistant for Bash and Zsh.

Warp helps you recall past shell commands, draft new commands from natural language, explain commands, and safely insert selected commands into your shell buffer — **without ever auto-executing anything**.

## Features

- **`warp ask "..."`** — generate shell commands from natural language, grounded in your history
- **`warp recall "..."`** — semantically retrieve past commands you half-remember
- **`warp search "..."`** — fast keyword search over your command history
- **`warp explain '...'`** — explain any command with risk warnings
- **Interactive selection** — pick a candidate and insert it into your shell buffer
- **Deterministic safety** — every generated command is analyzed for risk before you see it
- **Local-first** — your history stays on your machine

## Quick Start

```bash
# Install
pip install -e .

# Initialize config and database
warp config init

# Import your existing shell history
warp import-history

# Check everything is working
warp doctor
```

## Shell Setup

### Zsh (add to ~/.zshrc)

```zsh
if command -v warp &>/dev/null; then
    WARP_SHELL_DIR="$(python3 -c 'import warp.shell; import os; print(os.path.dirname(warp.shell.__file__))')"
    source "${WARP_SHELL_DIR}/zsh_integration.sh"
fi
```

### Bash (add to ~/.bashrc)

```bash
if command -v warp &>/dev/null; then
    WARP_SHELL_DIR="$(python3 -c 'import warp.shell; import os; print(os.path.dirname(warp.shell.__file__))')"
    source "${WARP_SHELL_DIR}/bash_integration.sh"
fi
```

After adding the integration, open a new terminal. Your commands will be captured automatically.

**Key bindings:**
- `Ctrl-F` — interactive history search
- `Alt-A` — AI command generation

## Example Commands

```bash
# AI-grounded command generation
warp ask "find large log files modified this week"
warp ask "compress the current directory"
warp ask "show top processes by memory"

# Semantic history recall
warp recall "the rsync backup command I used last month"
warp recall "how I checked disk usage"

# Keyword history search
warp search "git log"
warp search "find .py files"

# Explain a command
warp explain 'find . -name "*.log" -delete'
warp explain 'rm -rf /tmp/old_stuff'

# Interactive selection (inserts into shell buffer)
warp interactive-search
warp interactive-ask "list files by size"

# Print selected command to stdout (for shell buffer insertion)
warp ask "git stash" --print-only
```

## Configuration

Config file: `~/.config/warp/config.toml`

```toml
[warp]
model_backend = "rules"        # rules / openai / local
selector = "auto"              # auto / fzf / builtin
max_search_results = 20
history_retention_days = 365
ignore_leading_space_commands = true
prefer_preview_before_delete = true

# OpenAI backend (optional)
# openai_api_key = "sk-..."
# openai_model = "gpt-4o-mini"

# Local LLM backend (optional, e.g. Ollama)
# local_llm_url = "http://localhost:11434"
```

Or set `OPENAI_API_KEY` environment variable.

### Backends

| Backend | Description | Requires |
|---------|-------------|---------|
| `rules` | Deterministic, offline | Nothing |
| `openai` | GPT-4o-mini or similar | `OPENAI_API_KEY` + `pip install 'warp[openai]'` |
| `local` | Local LLM via Ollama/llama.cpp | Running local server |

## Safety Philosophy

Warp **never auto-executes** generated commands. Every candidate is analyzed by a deterministic safety layer that assigns risk levels (low / moderate / high) and suggests safer previews for destructive operations.

Examples:
- `find . -name "*.log" -delete` → suggests `find . -name "*.log" -print` first
- `rm *.tmp` → suggests `printf '%s\n' *.tmp` to preview matches
- `rm -rf /path` → flagged HIGH risk with warning

See [docs/safety.md](docs/safety.md) for more.

## Importing History

```bash
warp import-history                    # auto-detect shell
warp import-history --shell bash
warp import-history --shell zsh
warp import-history --file ~/.bash_history
warp import-history --dry-run          # preview without importing
```

## Current Limitations

- Semantic recall uses FTS + ranking (not vector embeddings) by default. An embeddings extension point exists in `embeddings.py`.
- The `rules` backend handles common patterns; complex requests need the `openai` backend.
- Shell buffer insertion via key bindings requires the shell integration scripts to be sourced.
- Windows is not currently supported.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run a specific test
pytest tests/test_safety.py -v
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for a detailed architecture overview.

## License

MIT
