"""SQLite database layer for warp command history."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from warp.models import CaptureRecord, SearchResult

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS commands (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    session_id      TEXT    NOT NULL,
    shell           TEXT    NOT NULL,
    cwd             TEXT    NOT NULL,
    repo_root       TEXT,
    hostname        TEXT    NOT NULL,
    username        TEXT    NOT NULL,
    command_raw     TEXT    NOT NULL,
    command_norm    TEXT    NOT NULL,
    verb            TEXT,
    exit_code       INTEGER NOT NULL DEFAULT 0,
    duration_ms     INTEGER,
    success         INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_commands_timestamp  ON commands(timestamp);
CREATE INDEX IF NOT EXISTS idx_commands_verb       ON commands(verb);
CREATE INDEX IF NOT EXISTS idx_commands_repo_root  ON commands(repo_root);
CREATE INDEX IF NOT EXISTS idx_commands_cwd        ON commands(cwd);

CREATE VIRTUAL TABLE IF NOT EXISTS commands_fts USING fts5(
    command_raw,
    command_norm,
    cwd,
    repo_root,
    verb,
    content='commands',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS commands_ai AFTER INSERT ON commands BEGIN
    INSERT INTO commands_fts(rowid, command_raw, command_norm, cwd, repo_root, verb)
    VALUES (new.id, new.command_raw, new.command_norm, new.cwd, new.repo_root, new.verb);
END;

CREATE TRIGGER IF NOT EXISTS commands_ad AFTER DELETE ON commands BEGIN
    INSERT INTO commands_fts(commands_fts, rowid, command_raw, command_norm, cwd, repo_root, verb)
    VALUES ('delete', old.id, old.command_raw, old.command_norm, old.cwd, old.repo_root, old.verb);
END;

CREATE TABLE IF NOT EXISTS ai_interactions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp               TEXT NOT NULL,
    request_text            TEXT NOT NULL,
    retrieved_command_ids   TEXT,
    generated_candidates_json TEXT,
    selected_candidate      TEXT,
    risk_summary            TEXT
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


def init_db(db_path: Path) -> None:
    """Initialize the database schema at the given path."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager returning a WAL-mode database connection."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_command(conn: sqlite3.Connection, record: CaptureRecord) -> int:
    """Insert a CaptureRecord into the commands table and return its id."""
    cursor = conn.execute(
        """
        INSERT INTO commands
            (timestamp, session_id, shell, cwd, repo_root, hostname, username,
             command_raw, command_norm, verb, exit_code, duration_ms, success)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.timestamp,
            record.session_id,
            record.shell,
            record.cwd,
            record.repo_root,
            record.hostname,
            record.username,
            record.command_raw,
            record.command_norm,
            record.verb,
            record.exit_code,
            record.duration_ms,
            record.success,
        ),
    )
    return cursor.lastrowid or 0


def fts_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[sqlite3.Row]:
    """Full-text search over the commands_fts virtual table."""
    try:
        rows = conn.execute(
            """
            SELECT c.*, bm25(commands_fts) AS fts_score
            FROM commands_fts
            JOIN commands c ON commands_fts.rowid = c.id
            WHERE commands_fts MATCH ?
            ORDER BY fts_score
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return rows
    except sqlite3.OperationalError:
        return []


def get_recent_commands(
    conn: sqlite3.Connection,
    limit: int = 20,
    cwd: Optional[str] = None,
) -> list[sqlite3.Row]:
    """Return the most recent commands, optionally filtered by cwd."""
    if cwd:
        return conn.execute(
            "SELECT * FROM commands WHERE cwd = ? ORDER BY timestamp DESC LIMIT ?",
            (cwd, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM commands ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()


def get_commands_by_repo(
    conn: sqlite3.Connection,
    repo_root: str,
    limit: int = 20,
) -> list[sqlite3.Row]:
    """Return commands from a specific repo root."""
    return conn.execute(
        "SELECT * FROM commands WHERE repo_root = ? ORDER BY timestamp DESC LIMIT ?",
        (repo_root, limit),
    ).fetchall()


def row_to_search_result(row: sqlite3.Row) -> SearchResult:
    """Convert a database row to a SearchResult."""
    return SearchResult(
        id=row["id"],
        command_raw=row["command_raw"],
        command_norm=row["command_norm"],
        cwd=row["cwd"],
        timestamp=row["timestamp"],
        exit_code=row["exit_code"],
        success=row["success"],
        repo_root=row["repo_root"],
        verb=row["verb"],
        session_id=row["session_id"],
        shell=row["shell"],
        hostname=row["hostname"],
        username=row["username"],
        duration_ms=row["duration_ms"],
    )


def get_last_command_in_session(
    conn: sqlite3.Connection,
    session_id: str,
    cwd: str,
) -> Optional[sqlite3.Row]:
    """Return the most recent command for the given session+cwd."""
    rows = conn.execute(
        """
        SELECT * FROM commands
        WHERE session_id = ? AND cwd = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (session_id, cwd),
    ).fetchall()
    return rows[0] if rows else None
