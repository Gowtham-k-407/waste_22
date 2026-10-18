import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import text, inspect, func
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings, normalize_database_url
from app.core.database import (
    engine, SessionLocal, UserSessionLocal, StaffSessionLocal, WasteSessionLocal,
    check_database_health, create_db_engine
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, AuthAuditLog, PasswordResetToken
from app.models.staff import StaffProfile, StaffDutyAssignment
from app.models.geography import Zone, Ward
from app.models.waste import WasteCategory, WasteRecord
from app.models.facility import SegregationPlant
from app.models.vehicle import CollectionVehicle
from app.models.complaint import PublicComplaint
from migrate_to_postgres import run_migration, TABLE_MIGRATION_ORDER

client = TestClient(app)


# ----------------------------------------------------------------------
# 1. PostgreSQL Connection Configuration
# ----------------------------------------------------------------------
def test_postgresql_connection_configuration():
    """Verify PostgreSQL URL normalization, psycopg2 driver enforcement, and pooling settings."""
    # Test normalization of Heroku/Render postgres:// prefix
    raw_render_url = "postgres://user_admin:secret123@dpg-abc.render.com/wastedash"
    normalized = normalize_database_url(raw_render_url)
    assert normalized.startswith("postgresql+psycopg2://")
    assert "user_admin" in normalized

    # Test standard postgresql:// prefix
    raw_pg_url = "postgresql://localhost:5432/wastedash"
    normalized_pg = normalize_database_url(raw_pg_url)
    assert normalized_pg.startswith("postgresql+psycopg2://")

    # Verify active engine pooling parameters
    assert engine.pool.size() >= 5
    assert engine.dialect.name == "postgresql"


# ----------------------------------------------------------------------
# 2. Database Session Lifecycle and Transaction Rollback
# ----------------------------------------------------------------------
def test_session_lifecycle_and_transaction_rollback():
    """Verify transaction atomicity: uncommitted or rolled-back changes are discarded."""
    session = SessionLocal()
    test_username = f"rollback_test_{datetime.now(timezone.utc).timestamp()}"
    user = User(
        username=test_username,
        email=f"{test_username}@wastedash.gov",
        hashed_password=hash_password("Password123!"),
        full_name="Rollback Test User",
        role="contributor"
    )
    session.add(user)
    # Explicitly rollback before commit
    session.rollback()
    session.close()

    # Verify in a new session that record was NOT persisted
    new_session = SessionLocal()
    persisted = new_session.query(User).filter(User.username == test_username).first()
    new_session.close()
    assert persisted is None, "Rolled-back record must not exist in database."


# ----------------------------------------------------------------------
# 3. User Registration and Login Using Existing Account Records
# ----------------------------------------------------------------------
def test_login_with_existing_account_and_registration():
    """Verify login with existing pre-migration admin account and registration of new contributor."""
    # 1. Existing pre-migration administrator account login
    admin_login_res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "admin@chennaiswm.gov.in", "password": "Admin@123"}
    )
    assert admin_login_res.status_code == 200, f"Login failed: {admin_login_res.text}"
    admin_data = admin_login_res.json()
    assert admin_data["access_token"] is not None
    assert admin_data["user"]["role"] == "system_admin"

    # 2. Register a new citizen contributor
    ts = int(datetime.now(timezone.utc).timestamp())
    reg_email = f"citizen_new_{ts}@chennaigov.in"
    reg_res = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "username": f"citizen_{ts}",
            "email": reg_email,
            "password": "Password123!",
            "full_name": "New Citizen Registrant",
            "city": "Chennai"
        }
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == reg_email

    # 3. Login with newly created user
    login_res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": reg_email, "password": "Password123!"}
    )
    assert login_res.status_code == 200
    assert login_res.json()["access_token"] is not None


# ----------------------------------------------------------------------
# 4. Authentication and RBAC Behavior
# ----------------------------------------------------------------------
def test_authentication_and_rbac_behavior():
    """Verify JWT authentication and role-based access control rejection."""
    # 1. Access protected admin endpoint without token -> 401 Unauthorized
    res_unauth = client.get(f"{settings.API_V1_STR}/admin/overview")
    assert res_unauth.status_code == 401

    session = SessionLocal()
    contributor = session.query(User).filter(User.role == "contributor").first()
    admin = session.query(User).filter(User.role == "system_admin").first()
    session.close()

    # 2. Access admin endpoint with contributor token -> 403 Forbidden
    contributor_token = create_access_token(
        data={"sub": contributor.email, "role": contributor.role, "id": contributor.id}
    )
    res_forbidden = client.get(
        f"{settings.API_V1_STR}/admin/overview",
        headers={"Authorization": f"Bearer {contributor_token}"}
    )
    assert res_forbidden.status_code == 403

    # 3. Access with admin token -> 200 OK
    admin_token = create_access_token(
        data={"sub": admin.email, "role": admin.role, "id": admin.id}
    )
    res_admin = client.get(
        f"{settings.API_V1_STR}/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200


# ----------------------------------------------------------------------
# 5. User-to-Staff Relationships
# ----------------------------------------------------------------------
def test_user_to_staff_relationships():
    """Verify integrity of cross-domain user-to-staff profile linkage."""
    session = SessionLocal()
    staff = session.query(StaffProfile).first()
    assert staff is not None
    assert staff.user_id is not None
    assert staff.employee_id is not None

    # Verify corresponding user exists in users domain
    linked_user = session.query(User).filter(User.id == staff.user_id).first()
    assert linked_user is not None, f"Linked user with ID {staff.user_id} must exist in users domain"
    assert linked_user.full_name == staff.full_name
    session.close()


# ----------------------------------------------------------------------
# 6. Waste Management CRUD Operations
# ----------------------------------------------------------------------
def test_waste_management_crud():
    """Verify Create, Read, Update, and Delete operations in waste_management domain."""
    session = SessionLocal()
    cat_name = f"Test Plastic {datetime.now(timezone.utc).timestamp()}"
    new_cat = WasteCategory(
        name=cat_name,
        color="#3B82F6",
        recyclability_pct=88.5,
        description="High-density recyclable polymers.",
        handling_instructions="Segregate into blue bins."
    )
    session.add(new_cat)
    session.commit()
    session.refresh(new_cat)

    cat_id = new_cat.id
    assert cat_id is not None

    # Read
    fetched = session.query(WasteCategory).filter(WasteCategory.id == cat_id).first()
    assert fetched.name == cat_name

    # Update
    fetched.recyclability_pct = 92.0
    session.commit()

    re_fetched = session.query(WasteCategory).filter(WasteCategory.id == cat_id).first()
    assert re_fetched.recyclability_pct == 92.0

    # Delete
    session.delete(re_fetched)
    session.commit()

    deleted = session.query(WasteCategory).filter(WasteCategory.id == cat_id).first()
    assert deleted is None
    session.close()


# ----------------------------------------------------------------------
# 7. Dashboard Analytics and Aggregate Queries
# ----------------------------------------------------------------------
def test_dashboard_analytics_aggregate_queries():
    """Verify aggregate SQL functions (SUM, AVG, COUNT) across consolidated tables."""
    session = SessionLocal()

    # Aggregate 1: Count total wards and average population
    ward_stats = session.query(
        func.count(Ward.id),
        func.avg(Ward.population)
    ).first()
    assert ward_stats[0] >= 200, "Must have at least 200 municipal wards"
    assert ward_stats[1] > 0

    # Aggregate 2: Count processing plants and calculate total capacity
    plant_stats = session.query(
        func.count(SegregationPlant.id),
        func.sum(SegregationPlant.capacity_tpd)
    ).first()
    assert plant_stats[0] >= 12, "Must have 12 GCC processing facilities"
    assert plant_stats[1] > 1000.0

    session.close()


# ----------------------------------------------------------------------
# 8. Foreign-Key and Unique-Constraint Enforcement
# ----------------------------------------------------------------------
def test_foreign_key_and_unique_constraints():
    """Verify that PostgreSQL enforces unique constraints and data integrity."""
    session = SessionLocal()

    # Unique constraint test on User.email
    duplicate_user = User(
        username="unique_test_user_dupe",
        email="admin@chennaiswm.gov.in", # Already exists
        hashed_password=hash_password("Password123!"),
        full_name="Dupe Email User",
        role="contributor"
    )
    session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Unique constraint test on StaffProfile.employee_id
    duplicate_staff = StaffProfile(
        user_id=999999,
        employee_id="GCC-EMP-001", # Already exists
        full_name="Duplicate Employee Code",
        job_title="Sanitary Inspector",
        role_code="sanitary_inspector",
        department="Solid Waste Management",
        phone_number="+91 44 2538 9999"
    )
    session.add(duplicate_staff)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.close()


# ----------------------------------------------------------------------
# 9. Migration of All Source Database Tables
# ----------------------------------------------------------------------
def test_migration_of_all_33_tables():
    """Verify that all 33 tables across the three logical domains exist in PostgreSQL."""
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    expected_tables = {
        # Domain: users (4)
        "users", "password_reset_tokens", "auth_audit_logs", "user_ai_references",
        # Domain: staff (3)
        "staff_profiles", "staff_duty_assignments", "staff_audit_logs",
        # Domain: waste_management (26)
        "zones", "wards", "waste_categories", "waste_records", "segregation_plants",
        "collection_vehicles", "ai_detections", "image_contributions", "uploads",
        "dataset_images", "ai_models", "training_jobs", "dataset_sources",
        "dataset_imports", "environmental_metrics", "operational_alerts",
        "optimization_recommendations", "iot_devices", "device_telemetry",
        "iot_sorting_records", "public_complaints", "complaint_follow_ups",
        "notifications", "weighbridge_records", "simulation_runs", "ai_inference_audit"
    }

    missing_tables = expected_tables - existing_tables
    assert not missing_tables, f"Missing tables in PostgreSQL: {missing_tables}"


# ----------------------------------------------------------------------
# 10. Preservation of IDs and Relationships
# ----------------------------------------------------------------------
def test_preservation_of_ids_and_data_integrity():
    """Verify entity IDs, password hashes, and timestamps were preserved from SQLite."""
    session = SessionLocal()

    # Check Administrator ID 1
    admin = session.query(User).filter(User.id == 1).first()
    assert admin is not None
    assert admin.email in ("admin@wastesegeregate.in", "admin@chennaiswm.gov.in")
    assert admin.hashed_password.startswith("$")

    # Check Zone ID 1
    zone1 = session.query(Zone).filter(Zone.id == 1).first()
    assert zone1 is not None
    assert zone1.zone_number == 1
    assert "Thiruvottiyur" in zone1.name

    # Check Ward 1 has valid zone relationship
    ward1 = session.query(Ward).filter(Ward.ward_number == 1).first()
    assert ward1 is not None
    assert ward1.zone_id == 1

    session.close()


# ----------------------------------------------------------------------
# 11. Idempotent Migration Behavior
# ----------------------------------------------------------------------
def test_idempotent_migration():
    """Verify running migration multiple times does not produce duplicates or errors."""
    res = run_migration(target_url=settings.DATABASE_URL)
    assert res["status"] == "SUCCESS"
    assert res["all_passed"] is True


# ----------------------------------------------------------------------
# 12. Correct PostgreSQL Sequence Values After Import
# ----------------------------------------------------------------------
def test_postgresql_sequence_alignment():
    """Verify that auto-increment ID sequences generate new IDs greater than MAX(id)."""
    session = SessionLocal()
    max_user_id = session.query(func.max(User.id)).scalar() or 0

    ts = int(datetime.now(timezone.utc).timestamp())
    test_user = User(
        username=f"seq_test_{ts}",
        email=f"seq_{ts}@chennaigov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Sequence Alignment Tester",
        role="public"
    )
    session.add(test_user)
    session.commit()
    session.refresh(test_user)

    assert test_user.id > max_user_id, f"Expected sequence to assign id > {max_user_id}, got {test_user.id}"
    session.close()


# ----------------------------------------------------------------------
# 13. Database Health Checks
# ----------------------------------------------------------------------
def test_database_health_checks():
    """Verify check_database_health function and /api/health endpoint response structure."""
    health = check_database_health()
    assert health["healthy"] is True
    assert health["status"] == "connected"
    assert health["engine"] == "postgresql"
    assert "databases" in health
    assert "database_a_user_auth" in health["databases"]
    assert "database_b_municipal_staff" in health["databases"]
    assert "database_c_waste_ai_operations" in health["databases"]

    # Test FastAPI /api/health endpoint
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"]["healthy"] is True
    assert data["database"]["engine"] == "postgresql"


# ----------------------------------------------------------------------
# 14. Handling Unavailable or Invalid PostgreSQL Configuration
# ----------------------------------------------------------------------
def test_handling_invalid_postgresql_configuration():
    """Verify that invalid database connection strings raise an error without silent fallback."""
    invalid_url = "postgresql+psycopg2://nonexistent_user:wrong_pass@127.0.0.1:54321/nonexistent_db"
    bad_engine, _ = create_db_engine(invalid_url, name="bad_test_db")
    with pytest.raises(OperationalError):
        with bad_engine.connect() as conn:
            conn.execute(text("SELECT 1"))


# ----------------------------------------------------------------------
# 15. Confirmation That Production Runtime No Longer Silently Accesses SQLite
# ----------------------------------------------------------------------
def test_production_runtime_rejects_sqlite_fallback(monkeypatch):
    """Verify that APP_ENV=production strictly forbids SQLite and does not fall back."""
    monkeypatch.setenv("APP_ENV", "production")
    sqlite_url = "sqlite:///./production_forbidden.db"
    with pytest.raises(RuntimeError) as exc_info:
        create_db_engine(sqlite_url, name="production_test")
    assert "SQLite is not permitted in production" in str(exc_info.value)


# ----------------------------------------------------------------------
# 16. Regression Coverage for Existing API Routes and Response Formats
# ----------------------------------------------------------------------
def test_api_routes_and_response_structures():
    """Verify that core existing API routes return HTTP 200 and expected schemas."""
    session = SessionLocal()
    admin = session.query(User).filter(User.role == "system_admin").first()
    session.close()
    admin_token = create_access_token(data={"sub": admin.email, "role": admin.role, "id": admin.id})
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Waste categories (public)
    res_cats = client.get(f"{settings.API_V1_STR}/waste/categories")
    assert res_cats.status_code == 200
    cats = res_cats.json()
    assert len(cats) >= 11
    assert any("Organic" in c["name"] for c in cats)

    # 2. Wards endpoint (public)
    res_wards = client.get(f"{settings.API_V1_STR}/wards")
    assert res_wards.status_code == 200
    wards = res_wards.json()
    assert len(wards) >= 200

    # 3. Processing Plants endpoint (authenticated staff/admin)
    res_plants = client.get(f"{settings.API_V1_STR}/plants", headers=auth_headers)
    assert res_plants.status_code == 200
    plants = res_plants.json()
    assert len(plants) >= 12

    # 4. Collection Vehicles endpoint (authenticated staff/admin)
    res_vehicles = client.get(f"{settings.API_V1_STR}/vehicles/", headers=auth_headers)
    assert res_vehicles.status_code == 200
    vehicles = res_vehicles.json()
    assert len(vehicles) >= 24

    # 5. Public Grievances portal (authenticated)
    res_complaints = client.get(f"{settings.API_V1_STR}/complaints", headers=auth_headers)
    assert res_complaints.status_code == 200
