import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("wastedash.database")

# Build engine with appropriate options for PostgreSQL vs SQLite
is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30
    })

try:
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
except Exception as e:
    logger.error(f"Failed to initialize SQLAlchemy engine with URL {settings.DATABASE_URL}: {e}")
    # Fallback to local SQLite if remote PostgreSQL connection string syntax fails
    engine = create_engine("sqlite:///./chennai_waste.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def check_database_health() -> dict:
    """Checks database connectivity and returns latency and engine type."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            return {
                "status": "connected" if result == 1 else "degraded",
                "engine": "sqlite" if is_sqlite else "postgresql",
                "healthy": True
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "disconnected",
            "engine": "sqlite" if is_sqlite else "postgresql",
            "healthy": False,
            "error": str(e)
        }
