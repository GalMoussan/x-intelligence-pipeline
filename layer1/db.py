"""
SQLite schema management for x-intelligence-pipeline.

Schema versions:
  1 — initial: tweets table
  2 — add fetch_runs table for run auditing

Run directly to initialise or migrate:
    python -m layer1.db
"""

import sqlite3
from pathlib import Path

from config import settings

CURRENT_VERSION = 2

# ---------------------------------------------------------------------------
# Migration definitions — list index = version number (index 0 unused)
# ---------------------------------------------------------------------------

MIGRATIONS: dict[int, str] = {
    1: """
        CREATE TABLE IF NOT EXISTS tweets (
            id          TEXT PRIMARY KEY,
            author_id   TEXT NOT NULL,
            username    TEXT NOT NULL,
            text        TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            fetched_at  TEXT NOT NULL,
            metrics     TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tweets_username   ON tweets (username);
        CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets (created_at);
    """,
    2: """
        CREATE TABLE IF NOT EXISTS fetch_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            accounts    INTEGER NOT NULL DEFAULT 0,
            tweets      INTEGER NOT NULL DEFAULT 0,
            dry_run     INTEGER NOT NULL DEFAULT 0,
            error       TEXT
        );
    """,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open (and create) the SQLite database, returning a connection."""
    path = Path(db_path or settings.SQLITE_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version stored in user_version pragma."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection, target: int = CURRENT_VERSION) -> None:
    """Apply all pending migrations up to `target` version."""
    current = get_schema_version(conn)
    if current >= target:
        return

    for version in range(current + 1, target + 1):
        sql = MIGRATIONS.get(version)
        if not sql:
            raise RuntimeError(f"No migration defined for version {version}")
        print(f"  Applying migration v{version}…")
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()

    print(f"Schema at version {target}.")


def init(db_path: str | None = None) -> sqlite3.Connection:
    """Open DB, run all pending migrations, return ready connection."""
    conn = get_connection(db_path)
    migrate(conn)
    return conn


# ---------------------------------------------------------------------------
# Run audit helpers (used by scraper)
# ---------------------------------------------------------------------------

def log_run_start(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Insert a fetch_run row and return its id."""
    from datetime import datetime, timezone
    cur = conn.execute(
        "INSERT INTO fetch_runs (started_at, dry_run) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), int(dry_run)),
    )
    conn.commit()
    return cur.lastrowid


def log_run_finish(
    conn: sqlite3.Connection,
    run_id: int,
    accounts: int,
    tweets: int,
    error: str | None = None,
) -> None:
    """Update fetch_run row with completion details."""
    from datetime import datetime, timezone
    conn.execute(
        """
        UPDATE fetch_runs
        SET finished_at = ?, accounts = ?, tweets = ?, error = ?
        WHERE id = ?
        """,
        (datetime.now(timezone.utc).isoformat(), accounts, tweets, error, run_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Initialising database at: {settings.SQLITE_DB_PATH}")
    conn = init()
    version = get_schema_version(conn)
    print(f"Done. Schema version: {version}")
    conn.close()
