"""Test configuration.

Must execute before app.config is imported: the suite pins DATABASE_URL to
memory:// so tests exercise the in-memory repository and never read or write
a real database file. SQLite behavior is covered separately by parity tests
that construct SqliteRepository directly against a temporary file.
"""

import os

os.environ["DATABASE_URL"] = "memory://"
