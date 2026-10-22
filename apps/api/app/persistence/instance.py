"""Configured repository singleton.

Chosen once from DATABASE_URL at import time. Tests set DATABASE_URL=memory://
in conftest.py before importing the app, so the test suite never touches a
real database file.
"""

from app.config import settings
from app.persistence.repository import make_repository

repository = make_repository(settings.database_url)