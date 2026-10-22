"""Database URL parsing and connection management.

Supported DATABASE_URL schemes:
- sqlite:///relative/path.db  (resolved against the repository root, NOT the
  process working directory — so the same config yields the same file no
  matter where the server is started from)
- sqlite:////absolute/path.db
- memory://                   (in-process, non-durable; used by tests)

Connection policy: one connection per call, WAL journal mode. FastAPI runs
sync endpoints in a threadpool, so concurrent readers plus a single writer is
the expected pattern; WAL handles it without reader/writer blocking.
"""

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SUPPORTED_SCHEMES = ("sqlite", "memory")


def resolve_sqlite_path(database_url: str) -> Path:
    """Convert a sqlite URL into a concrete file path.

    sqlite:///./ghostrange.db -> REPO_ROOT/ghostrange.db
    sqlite:////tmp/x.db       -> /tmp/x.db
    """
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"unsupported database URL: {database_url!r}")
    raw_path = database_url[len(prefix):]
    path = Path(raw_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(database_url: str) -> sqlite3.Connection:
    """Open a configured SQLite connection. Caller must close it."""
    if database_url == "memory://":
        connection = sqlite3.connect(":memory:")
    elif database_url.startswith("sqlite:///"):
        connection = sqlite3.connect(resolve_sqlite_path(database_url))
    else:
        raise ValueError(f"unsupported database URL: {database_url!r}")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection