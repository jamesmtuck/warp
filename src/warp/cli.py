"""Command-line interface for warp."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer

from warp.config import WarpConfig, default_config, get_default_config_path, load_config, save_config
from warp.constants import DEFAULT_DB_PATH
from warp.version import __version__

app = typer.Typer(
    name="warp",
    help="Local-first AI-powered terminal assistant.",
    add_completion=False,
    no_args_is_help=True,
)

config_app = typer.Typer(help="Configuration management.")
app.add_typer(config_app, name="config")


def _get_config(config_path: Optional[Path] = None) -> WarpConfig:
    """Load config, creating defaults if needed."""
    return load_config(config_path)


def _get_db_path(config: WarpConfig) -> Path:
    return Path(config.db_path)


def _ensure_db(db_path: Path) -> None:
    """Initialize the database schema if needed."""
    from warp.db import init_db
    init_db(db_path)


# ---------------------------------------------------------------------------
# warp ask
# ---------------------------------------------------------------------------
@app.command()
def ask(
    request: str = typer.Argument(..., help="Natural language request for a shell command."),
    print_only: bool = typer.Option(False, "--print-only", help="Print selected command to stdout only."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Override current working directory."),
    shell: Optional[str] = typer.Option(None, "--shell", help="Override shell type."),
) -> None:
    """Generate shell command candidates from a natural language request."""
    from warp.orchestration import generate_candidates
    from warp.selectors import select_from_items
    from warp.utils import print_candidates

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    effective_cwd = cwd or os.getcwd()

    candidates = generate_candidates(
        request=request,
        db_path=db_path,
        config=config,
        cwd=effective_cwd,
        shell=shell,
    )

    if not candidates:
        typer.echo("No candidates generated.", err=True)
        raise typer.Exit(1)

    if print_only:
        # Interactive selection, then print only the command
        items = [c.command for c in candidates]
        selected = select_from_items(items, selector=config.selector)
        if selected:
            print(selected, end="")
        return

    print_candidates(candidates, title=f"Candidates for: {request}\n")


# ---------------------------------------------------------------------------
# warp recall
# ---------------------------------------------------------------------------
@app.command()
def recall(
    query: str = typer.Argument(..., help="Natural language description of a past command."),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of results."),
) -> None:
    """Semantically recall past commands from your history."""
    from warp.retrieval import retrieve_similar_commands

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    results = retrieve_similar_commands(
        query=query,
        db_path=db_path,
        config=config,
        cwd=os.getcwd(),
        limit=limit,
    )

    if not results:
        typer.echo("No matching commands found.")
        return

    for i, r in enumerate(results, 1):
        status = "✓" if r.success else "✗"
        typer.echo(f"  [{i}] {status}  {r.command_raw}  ({r.cwd})")


# ---------------------------------------------------------------------------
# warp search
# ---------------------------------------------------------------------------
@app.command()
def search(
    query: str = typer.Argument(..., help="Keyword search over command history."),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Filter by working directory."),
) -> None:
    """Deterministic keyword search over command history."""
    from warp.search import search_history

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    results = search_history(
        query=query,
        db_path=db_path,
        config=config,
        cwd=cwd,
        limit=limit,
    )

    if not results:
        typer.echo("No matching commands found.")
        return

    for i, r in enumerate(results, 1):
        status = "✓" if r.success else "✗"
        typer.echo(f"  [{i}] {status}  {r.command_raw}  ({r.cwd})")


# ---------------------------------------------------------------------------
# warp explain
# ---------------------------------------------------------------------------
@app.command()
def explain(
    command: str = typer.Argument(..., help="Shell command to explain."),
) -> None:
    """Explain a shell command and warn about risk."""
    from warp.explain import explain_command

    result = explain_command(command)

    typer.echo(f"Command: {command}")
    typer.echo(f"Explanation: {result['explanation']}")
    if result["flags"]:
        typer.echo(f"Flags: {', '.join(result['flags'])}")
    typer.echo(f"Risk level: {result['risk_level'].upper()}")
    for w in result["warnings"]:
        typer.echo(f"  ⚠  {w}")
    if result.get("safer_preview"):
        typer.echo(f"Safer preview: {result['safer_preview']}")


# ---------------------------------------------------------------------------
# warp interactive-search
# ---------------------------------------------------------------------------
@app.command(name="interactive-search")
def interactive_search(
    print_only: bool = typer.Option(False, "--print-only", help="Print selected command to stdout only."),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Pre-filter query."),
) -> None:
    """Interactively search history and select a command."""
    from warp.search import search_history
    from warp.selectors import select_from_items

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    if query:
        results = search_history(query=query, db_path=db_path, config=config, cwd=os.getcwd())
    else:
        from warp.db import get_connection, get_recent_commands, row_to_search_result
        with get_connection(db_path) as conn:
            rows = get_recent_commands(conn, limit=config.max_search_results)
            results = [row_to_search_result(r) for r in rows]

    if not results:
        typer.echo("No commands in history.", err=True)
        raise typer.Exit(1)

    items = [r.command_raw for r in results]
    selected = select_from_items(items, selector=config.selector)

    if selected:
        if print_only:
            print(selected, end="")
        else:
            typer.echo(f"Selected: {selected}")


# ---------------------------------------------------------------------------
# warp interactive-ask
# ---------------------------------------------------------------------------
@app.command(name="interactive-ask")
def interactive_ask(
    request: str = typer.Argument(..., help="Natural language request."),
    print_only: bool = typer.Option(False, "--print-only", help="Print selected command to stdout only."),
) -> None:
    """Generate candidates and interactively select one."""
    from warp.orchestration import generate_candidates
    from warp.selectors import select_from_items
    from warp.utils import print_candidates

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    candidates = generate_candidates(
        request=request,
        db_path=db_path,
        config=config,
        cwd=os.getcwd(),
    )

    if not candidates:
        typer.echo("No candidates generated.", err=True)
        raise typer.Exit(1)

    if not print_only:
        print_candidates(candidates)

    items = [c.command for c in candidates]
    selected = select_from_items(items, selector=config.selector)

    if selected:
        if print_only:
            print(selected, end="")
        else:
            typer.echo(f"\nSelected: {selected}")


# ---------------------------------------------------------------------------
# warp next
# ---------------------------------------------------------------------------
@app.command(name="next")
def next_command(
    last: Optional[str] = typer.Option(
        None, "--last", help="The last command you ran (inferred from history if omitted)."
    ),
    print_only: bool = typer.Option(
        False, "--print-only", help="Print the selected command to stdout only (for shell integration)."
    ),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of predictions to show."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Override current working directory."),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Shell session ID for context."),
) -> None:
    """Predict and select likely next commands based on history patterns.

    Warp analyses your command history to surface what you are most likely
    to run next, taking recent sequential patterns and the current directory
    context into account.  Select a suggestion to copy it to your prompt or
    run it directly.

    Tip – add a shell alias for quick access:

      alias wn='eval "$(warp next --print-only)"'
    """
    from warp.db import get_connection, get_most_recent_command, row_to_search_result
    from warp.git_context import get_repo_root
    from warp.prediction import predict_next_commands
    from warp.selectors import select_from_items

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    effective_cwd = cwd or os.getcwd()
    effective_repo_root = get_repo_root(effective_cwd)

    # Infer last command from DB when not supplied on the command line
    last_cmd = last
    if last_cmd is None:
        effective_session = session_id or os.environ.get("WARP_SESSION_ID")
        with get_connection(db_path) as conn:
            row = get_most_recent_command(conn, session_id=effective_session)
        if row:
            last_cmd = row_to_search_result(row).command_raw

    predictions = predict_next_commands(
        db_path=db_path,
        config=config,
        last_command=last_cmd,
        cwd=effective_cwd,
        repo_root=effective_repo_root,
        session_id=session_id or os.environ.get("WARP_SESSION_ID"),
        limit=limit,
    )

    if not predictions:
        typer.echo("No predictions available yet – run more commands to build history.", err=True)
        raise typer.Exit(1)

    if not print_only:
        if last_cmd:
            typer.echo(f"Last command: {last_cmd}", err=True)
        typer.echo("Predicted next commands:", err=True)
        for i, p in enumerate(predictions, 1):
            reasons = ", ".join(p.reasons) if p.reasons else ""
            typer.echo(f"  [{i}] {p.command}  ({reasons})", err=True)
        typer.echo("", err=True)

    items = [p.command for p in predictions]
    selected = select_from_items(items, prompt="Next> ", selector=config.selector)

    if selected:
        if print_only:
            print(selected, end="")
        else:
            typer.echo(f"Selected: {selected}")


# ---------------------------------------------------------------------------
# warp capture  (internal, used by shell hooks)
# ---------------------------------------------------------------------------
@app.command()
def capture(
    command: str = typer.Argument(..., help="Command to capture."),
    exit_code: int = typer.Option(0, "--exit-code", help="Exit code of the command."),
    shell: str = typer.Option("bash", "--shell", help="Shell type."),
    cwd: str = typer.Option("", "--cwd", help="Working directory."),
    session_id: str = typer.Option("", "--session-id", help="Shell session ID."),
    duration_ms: Optional[int] = typer.Option(None, "--duration-ms", help="Duration in ms."),
) -> None:
    """Capture a shell command (called by shell hooks)."""
    from warp.capture import capture_command

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    effective_cwd = cwd or os.getcwd()
    effective_session = session_id or os.environ.get("WARP_SESSION_ID", "unknown")

    capture_command(
        db_path=db_path,
        config=config,
        command=command,
        exit_code=exit_code,
        shell=shell,
        cwd=effective_cwd,
        session_id=effective_session,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# warp doctor
# ---------------------------------------------------------------------------
@app.command()
def doctor() -> None:
    """Check environment, config, and installation."""
    from warp.doctor import run_doctor
    code = run_doctor()
    raise typer.Exit(code)


# ---------------------------------------------------------------------------
# warp config init / show
# ---------------------------------------------------------------------------
@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config."),
) -> None:
    """Initialize warp configuration."""
    from warp.db import init_db

    config_path = get_default_config_path()

    if config_path.exists() and not force:
        typer.echo(f"Config already exists at {config_path}. Use --force to overwrite.")
        return

    cfg = default_config()
    save_config(cfg, config_path=config_path)

    db_path = Path(cfg.db_path)
    init_db(db_path)

    typer.echo(f"Config initialized at {config_path}")
    typer.echo(f"Database initialized at {db_path}")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    config_path = get_default_config_path()
    cfg = load_config(config_path)
    typer.echo(f"Config path:    {config_path}")
    typer.echo(f"Data dir:       {cfg.data_dir}")
    typer.echo(f"Database:       {cfg.db_path}")
    typer.echo(f"Backend:        {cfg.model_backend}")
    typer.echo(f"Selector:       {cfg.selector}")
    typer.echo(f"Max results:    {cfg.max_search_results}")
    typer.echo(f"History days:   {cfg.history_retention_days}")


# ---------------------------------------------------------------------------
# warp import-history
# ---------------------------------------------------------------------------
@app.command(name="import-history")
def import_history(
    shell_type: Optional[str] = typer.Option(None, "--shell", help="Shell type: bash or zsh. Auto-detected if omitted."),
    history_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to history file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported without importing."),
) -> None:
    """Import command history from .bash_history or .zsh_history."""
    from warp.history_import import import_shell_history

    config = _get_config()
    db_path = _get_db_path(config)
    _ensure_db(db_path)

    count = import_shell_history(
        db_path=db_path,
        config=config,
        shell_type=shell_type,
        history_file=Path(history_file) if history_file else None,
        dry_run=dry_run,
    )

    if dry_run:
        typer.echo(f"Would import {count} commands.")
    else:
        typer.echo(f"Imported {count} commands.")


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context = typer.Option(None, hidden=True),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit.", is_eager=True),
) -> None:
    """Warp: local-first AI-powered terminal assistant."""
    if version:
        typer.echo(f"warp {__version__}")
        raise typer.Exit()
