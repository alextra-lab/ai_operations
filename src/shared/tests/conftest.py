import sys
from pathlib import Path

# Add the src directory to Python path so shared modules can be imported
src_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_dir))

# Set environment variables for testing
import os

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("POSTGRES_USER", "testuser")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password_123")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "aio-test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://testuser:test_password_123@localhost:5433/aio-test",
)
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_testing_only_32_chars")
