# Warp Architecture

## Overview

Warp is a local-first AI-powered terminal assistant structured as a Python package with a thin shell integration layer.

```
User's Shell (Bash/Zsh)
       │
       ├─ Shell hooks (preexec/precmd) ──► warp capture  ──► SQLite DB
       │
       └─ User invokes `warp ask "..."` or `warp search "..."`
              │
              ▼
         CLI (cli.py / typer)
              │
              ▼
         Orchestration Layer
           ├─ Context Builder  ──► shell, cwd, git repo, OS
           ├─ Retrieval Layer  ──► FTS + ranking over SQLite history
           ├─ Preferences      ──► inferred tool/risk preferences
           ├─ Backend          ──► rules / openai / local LLM
           ├─ Structured Output ─► parse + validate JSON
           └─ Safety Layer     ──► deterministic risk analysis
              │
              ▼
         CandidateCommand objects
              │
              ▼
         Selector (fzf / builtin menu)
              │
              ▼
         Selected command printed to stdout
         (Shell inserts into buffer — never auto-executes)
```

## Module Map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Typer CLI entry points |
| `config.py` | TOML config load/save (XDG paths) |
| `constants.py` | Project-wide constants |
| `models.py` | Core dataclasses |
| `db.py` | SQLite + FTS5 schema and helpers |
| `capture.py` | Shell hook capture with filtering/dedup |
| `normalize.py` | Lightweight command normalization |
| `git_context.py` | Git repo root detection |
| `ranking.py` | BM25 + contextual scoring |
| `search.py` | Deterministic FTS search |
| `retrieval.py` | Semantic-style retrieval (FTS + ranking) |
| `embeddings.py` | Placeholder for vector embeddings |
| `preferences.py` | Infer tool/risk preferences |
| `safety.py` | Deterministic risk analysis |
| `explain.py` | Rule-based command explanation |
| `context_builder.py` | Assemble WarpContext for AI |
| `prompting.py` | Build prompts for backends |
| `structured_output.py` | Parse + validate model JSON |
| `orchestration.py` | Tie all layers together |
| `selectors.py` | fzf / builtin interactive selection |
| `doctor.py` | Environment check |
| `history_import.py` | Import bash/zsh history |
| `utils.py` | Shared utility functions |
| `backends/rule_backend.py` | Deterministic command generation |
| `backends/openai_backend.py` | OpenAI API backend |
| `backends/local_llm_backend.py` | Local LLM adapter (Ollama) |
| `shell/bash_integration.sh` | Bash hooks |
| `shell/zsh_integration.sh` | Zsh hooks |

## Data Flow: `warp ask "find large log files"`

1. CLI receives request
2. `context_builder.build_context()` gathers: cwd, shell, git repo, OS, recent commands, retrieved similar commands, preference summary
3. `orchestration.generate_candidates()` calls the configured backend
4. Backend returns structured JSON with 1–3 command candidates
5. `structured_output.candidates_from_parsed()` validates and parses
6. `safety.analyze_command_risk()` is applied to every candidate
7. Results are printed; user selects one
8. Selected command is printed to stdout for shell insertion (never executed)

## Storage

SQLite database with WAL mode at `~/.local/share/warp/warp.db`:

- `commands` table: full command history with metadata
- `commands_fts` FTS5 virtual table: full-text search index
- `ai_interactions` table: optional AI interaction log
- `user_preferences` table: optional key-value preferences

## Extension Points

- **Embeddings**: `embeddings.py` is a stub. Replace `embed_text()` and `semantic_search()` with a real embedding backend.
- **New backends**: Subclass `ModelBackend` in `backends/model_base.py`.
- **New shell hooks**: Follow the pattern in `bash_integration.sh`/`zsh_integration.sh`.
