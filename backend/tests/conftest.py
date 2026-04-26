"""
Pytest configuration for imobiliarias-data tests.

Ensures the app module is importable and uses SQLite for testing
instead of requiring a PostgreSQL connection.
"""
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Override DATABASE_URL to use SQLite for testing so we don't need psycopg2
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
