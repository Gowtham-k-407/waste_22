import os
import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("wastedash.database")

def create_db_engine(url: str, name: str = "consolidated_wastedash"):
    """
    Creates a single SQLAlchemy engine for the consolidated PostgreSQL database.
    Enforces connection pooling, pre-ping validation, and rejects silent SQLite fallbacks in production.
    """
    if not url:
        logger.warning(f"DATABASE_URL is not set for {name}. Database operations will report disconnected status.")
        url = "postgresql+psycopg2://unconfigured_db_host:5432/unconfigured_db"

    is_sqlite = "sqlite" in url.lower()
    if is_sqlite:
        # SQLite is disallowed in production runtime; permitted only for tests/migration utility
        if os.getenv("APP_ENV", "").lower() == "production":
            raise RuntimeError(
                "SQLite is not permitted in production. WasteDash requires a consolidated PostgreSQL database configured via DATABASE_URL."
            )
        engine_kwargs = {"connect_args": {"check_same_thread": False, "timeout": 15}}
    else:
        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30
        }

    try:
        eng = create_engine(url, **engine_kwargs)
        if is_sqlite:
            @event.listens_for(eng, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA busy_timeout=5000")
                finally:
                    cursor.close()
        return eng, is_sqlite
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL {name} engine with URL {url}: {e}")
        # Explicit error reporting without silent fallback to SQLite
        raise

# -------------------------------------------------------------
# CONSOLIDATED POSTGRESQL ENGINE AND METADATA
# -------------------------------------------------------------
engine, is_sqlite = create_db_engine(settings.DATABASE_URL, "consolidated_wastedash")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------------------------------------------------
# THREE LOGICAL DOMAINS (Users, Staff, Waste Management)
# Shared across the single consolidated PostgreSQL schema & connection pool
# -------------------------------------------------------------
UserBase = Base
StaffBase = Base
WasteBase = Base

# Backward compatibility bindings
user_engine = engine
staff_engine = engine
waste_engine = engine

UserSessionLocal = SessionLocal
StaffSessionLocal = SessionLocal
WasteSessionLocal = SessionLocal

is_user_sqlite = is_sqlite
is_staff_sqlite = is_sqlite
is_waste_sqlite = is_sqlite

# -------------------------------------------------------------
# FastAPI Dependency Injectors
# -------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Domain dependency injectors (all backed by the consolidated PostgreSQL database)
get_user_db = get_db
get_staff_db = get_db
get_waste_db = get_db

# -------------------------------------------------------------
# Health Check Functions
# -------------------------------------------------------------
def check_single_database_health(eng, db_name: str, is_sql: bool) -> dict:
    try:
        with eng.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return {
                "name": db_name,
                "status": "connected" if result == 1 else "degraded",
                "engine": "sqlite" if is_sql else "postgresql",
                "healthy": True
            }
    except Exception as e:
        logger.error(f"{db_name} health check failed: {e}")
        return {
            "name": db_name,
            "status": "disconnected",
            "engine": "sqlite" if is_sql else "postgresql",
            "healthy": False,
            "error": str(e)
        }

def check_database_health() -> dict:
    """Checks consolidated PostgreSQL database health and verifies domain accessibility."""
    engine_type = "sqlite" if is_sqlite else "postgresql"
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            healthy = (result == 1)
            status = "connected" if healthy else "degraded"
            return {
                "status": status,
                "healthy": healthy,
                "engine": engine_type,
                "database_url_configured": bool(settings.DATABASE_URL),
                "logical_domains": ["users", "staff", "waste_management"],
                "databases": {
                    "database_a_user_auth": {
                        "name": "users_domain",
                        "status": status,
                        "engine": engine_type,
                        "healthy": healthy
                    },
                    "database_b_municipal_staff": {
                        "name": "staff_domain",
                        "status": status,
                        "engine": engine_type,
                        "healthy": healthy
                    },
                    "database_c_waste_ai_operations": {
                        "name": "waste_management_domain",
                        "status": status,
                        "engine": engine_type,
                        "healthy": healthy
                    }
                }
            }
    except Exception as e:
        logger.error(f"Consolidated database health check failed: {e}")
        return {
            "status": "disconnected",
            "healthy": False,
            "engine": engine_type,
            "error": str(e),
            "logical_domains": ["users", "staff", "waste_management"],
            "databases": {
                "database_a_user_auth": {"name": "users_domain", "status": "disconnected", "engine": engine_type, "healthy": False},
                "database_b_municipal_staff": {"name": "staff_domain", "status": "disconnected", "engine": engine_type, "healthy": False},
                "database_c_waste_ai_operations": {"name": "waste_management_domain", "status": "disconnected", "engine": engine_type, "healthy": False}
            }
        }
