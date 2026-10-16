import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("wastedash.database")

def create_db_engine(url: str, name: str):
    is_sqlite = "sqlite" in url.lower()
    engine_kwargs = {}
    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
    else:
        engine_kwargs.update({
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30
        })
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
        logger.error(f"Failed to initialize {name} engine with URL {url}: {e}")
        # Safe fallback to local SQLite for development
        fallback_url = f"sqlite:///./{name.lower()}.db"
        eng = create_engine(fallback_url, connect_args={"check_same_thread": False, "timeout": 15})
        @event.listens_for(eng, "connect")
        def set_sqlite_pragma_fb(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()
        return eng, True

# -------------------------------------------------------------
# DATABASE A: USER AND AUTHENTICATION DATABASE
# -------------------------------------------------------------
user_engine, is_user_sqlite = create_db_engine(settings.USER_DATABASE_URL, "users")
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
UserBase = declarative_base()

# -------------------------------------------------------------
# DATABASE B: MUNICIPAL STAFF AND WORKER DATABASE
# -------------------------------------------------------------
staff_engine, is_staff_sqlite = create_db_engine(settings.STAFF_DATABASE_URL, "staff")
StaffSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=staff_engine)
StaffBase = declarative_base()

# -------------------------------------------------------------
# DATABASE C: WASTE MANAGEMENT AND AI OPERATIONS DATABASE
# -------------------------------------------------------------
waste_engine, is_waste_sqlite = create_db_engine(settings.WASTE_DATABASE_URL, "waste_management")
WasteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=waste_engine)
WasteBase = declarative_base()

# Backward compatibility bindings
engine = waste_engine
SessionLocal = WasteSessionLocal
Base = WasteBase
is_sqlite = is_waste_sqlite

# -------------------------------------------------------------
# FastAPI Dependency Injectors
# -------------------------------------------------------------
def get_user_db():
    db = UserSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_staff_db():
    db = StaffSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_waste_db():
    db = WasteSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Alias for standard waste DB operations
get_db = get_waste_db

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
    """Checks all three databases independently and returns status."""
    user_health = check_single_database_health(user_engine, "user_database", is_user_sqlite)
    staff_health = check_single_database_health(staff_engine, "staff_database", is_staff_sqlite)
    waste_health = check_single_database_health(waste_engine, "waste_operations_database", is_waste_sqlite)

    all_healthy = user_health["healthy"] and staff_health["healthy"] and waste_health["healthy"]
    return {
        "status": "connected" if all_healthy else "degraded",
        "healthy": all_healthy,
        "engine": "sqlite" if is_waste_sqlite else "postgresql",
        "databases": {
            "database_a_user_auth": user_health,
            "database_b_municipal_staff": staff_health,
            "database_c_waste_ai_operations": waste_health
        }
    }
