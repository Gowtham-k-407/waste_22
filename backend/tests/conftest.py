import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import text

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Ensure embedded postgres server is available for tests if external DATABASE_URL is not set
TEST_PGDATA = Path("/tmp/test_pgdata")

def pytest_configure(config):
    """Sets up PostgreSQL test environment before test collection."""
    current_url = os.environ.get("DATABASE_URL", "")
    if not current_url or "sqlite" in current_url.lower():
        try:
            import embedded_postgres
            server = embedded_postgres.get_server(TEST_PGDATA, cleanup_mode=None)
            server.ensure_postgres_running()
            pg_url = server.get_uri("postgres").replace("postgresql://", "postgresql+psycopg2://")
            os.environ["DATABASE_URL"] = pg_url
            os.environ["USER_DATABASE_URL"] = pg_url
            os.environ["STAFF_DATABASE_URL"] = pg_url
            os.environ["WASTE_DATABASE_URL"] = pg_url
        except Exception as e:
            # If embedded postgres is not available, proceed with configured environment
            pass

    # Ensure tables and domains are created in the test PostgreSQL database
    try:
        from app.core.database import engine, Base, SessionLocal
        from app.services.seed_service import seed_all_databases
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS users;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS staff;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS waste_management;"))
        Base.metadata.create_all(bind=engine)
        seed_all_databases()
    except Exception as init_err:
        pass


@pytest.fixture(scope="session")
def pg_engine():
    from app.core.database import engine
    return engine


@pytest.fixture(scope="function")
def db_session():
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
