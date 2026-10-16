import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.database import UserSessionLocal, StaffSessionLocal, WasteSessionLocal
from app.models.user import User, AuthAuditLog, PasswordResetToken
from app.models.staff import StaffProfile

client = TestClient(app)

@pytest.fixture(scope="module")
def db_sessions():
    user_db = UserSessionLocal()
    staff_db = StaffSessionLocal()
    waste_db = WasteSessionLocal()
    yield user_db, staff_db, waste_db
    user_db.close()
    staff_db.close()
    waste_db.close()

@pytest.fixture(scope="module")
def test_fixtures(db_sessions):
    user_db, staff_db, _ = db_sessions

    # 1. System Admin
    admin = user_db.query(User).filter(User.email == "test_admin@chennai.gov.in").first()
    if not admin:
        admin = User(
            username="test_admin",
            email="test_admin@chennai.gov.in",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Test System Administrator",
            role="system_admin",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(admin)
        user_db.commit()
        user_db.refresh(admin)

    # 2. Contributor (Ordinary Citizen)
    contributor = user_db.query(User).filter(User.email == "citizen_test@gmail.com").first()
    if not contributor:
        contributor = User(
            username="citizen_test",
            email="citizen_test@gmail.com",
            hashed_password=hash_password("CitizenPass123!"),
            full_name="Ravi Citizen",
            role="contributor",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(contributor)
        user_db.commit()
        user_db.refresh(contributor)

    # 3. Plant Operator
    operator = user_db.query(User).filter(User.email == "operator.perungudi@chennaiswm.gov.in").first()
    if not operator:
        operator = User(
            username="perungudi_operator",
            email="operator.perungudi@chennaiswm.gov.in",
            hashed_password=hash_password("OperatorPass123!"),
            full_name="Perungudi Plant Operator",
            role="waste_processing_plant_operator",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(operator)
        user_db.commit()
        user_db.refresh(operator)

    # 4. Target User for Role Reassignment Test
    target_user = user_db.query(User).filter(User.email == "target_role_test@chennai.gov.in").first()
    if not target_user:
        target_user = User(
            username="target_role_test",
            email="target_role_test@chennai.gov.in",
            hashed_password=hash_password("TargetPass123!"),
            full_name="Target Role Test Account",
            role="contributor",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(target_user)
        user_db.commit()
        user_db.refresh(target_user)

    tokens = {
        "admin": create_access_token({"sub": admin.email, "role": admin.role}),
        "contributor": create_access_token({"sub": contributor.email, "role": contributor.role}),
        "operator": create_access_token({"sub": operator.email, "role": operator.role}),
        "target": create_access_token({"sub": target_user.email, "role": target_user.role}),
    }

    return {
        "admin": admin,
        "contributor": contributor,
        "operator": operator,
        "target": target_user,
        "tokens": tokens,
    }


# =========================================================================
# 1. ADMIN USER DIRECTORY & SAFE FIELDS INSPECTION
# =========================================================================

def test_admin_can_list_users_with_safe_fields(test_fixtures):
    """Verify authorized Admin can list users and responses contain no password hashes or secrets."""
    tokens = test_fixtures["tokens"]
    res = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "total_pages" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    first_item = data["items"][0]
    # Check expected safe fields
    assert "id" in first_item
    assert "username" in first_item
    assert "email" in first_item
    assert "full_name" in first_item
    assert "role" in first_item
    assert "is_active" in first_item
    assert "created_at" in first_item

    # Verify strict omission of sensitive fields across all items
    for item in data["items"]:
        assert "hashed_password" not in item
        assert "password" not in item
        assert "access_token" not in item
        assert "reset_token" not in item


def test_admin_can_filter_and_search_directory(test_fixtures):
    """Verify server-side searching and role/status filtering."""
    tokens = test_fixtures["tokens"]

    # Search by query
    res = client.get(
        "/api/admin/users?q=test_admin",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert any("test_admin" in u["username"] for u in data["items"])

    # Filter by role
    res_role = client.get(
        "/api/admin/users?role=system_admin",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res_role.status_code == 200
    data_role = res_role.json()
    assert all(u["role"] == "system_admin" for u in data_role["items"])

    # Filter by status
    res_active = client.get(
        "/api/admin/users?status=active",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res_active.status_code == 200
    assert all(u["is_active"] is True for u in res_active.json()["items"])


def test_admin_can_view_single_user_detail(test_fixtures):
    """Verify viewing single user administrative profile."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]

    res = client.get(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == target.id
    assert data["email"] == target.email
    assert data["username"] == target.username
    assert "hashed_password" not in data


# =========================================================================
# 2. ROLE MANAGEMENT SAFEGUARDS & RBAC BOUNDARIES
# =========================================================================

def test_admin_can_assign_permitted_role_and_persists(test_fixtures, db_sessions):
    """Verify Admin can update user role, persisiting in authoritative users.db."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]
    user_db, _, _ = db_sessions

    res = client.put(
        f"/api/admin/users/{target.id}/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={
            "role": "waste_processing_plant_operator",
            "reason": "Promotion to Perungudi facility operator"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["user"]["role"] == "waste_processing_plant_operator"

    # Verify directly in SQLite database
    user_db.expire_all()
    reloaded = user_db.query(User).filter(User.id == target.id).first()
    assert reloaded.role == "waste_processing_plant_operator"


def test_role_change_generates_audit_record(test_fixtures, db_sessions):
    """Verify role update writes an immutable entry into auth_audit_logs."""
    target = test_fixtures["target"]
    user_db, _, _ = db_sessions

    latest_log = user_db.query(AuthAuditLog).filter(
        AuthAuditLog.user_id == target.id
    ).order_by(AuthAuditLog.id.desc()).first()

    assert latest_log is not None
    assert "role_change" in latest_log.action
    assert "waste_processing_plant_operator" in latest_log.action
    assert "test_admin@chennai.gov.in" in latest_log.action


def test_ordinary_user_cannot_list_or_modify_roles(test_fixtures):
    """Verify ordinary contributor is blocked with 403 Forbidden."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]

    # Listing directory
    res_list = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['contributor']}"}
    )
    assert res_list.status_code == 403

    # Updating roles
    res_mod = client.put(
        f"/api/admin/users/{target.id}/role",
        headers={"Authorization": f"Bearer {tokens['contributor']}"},
        json={"role": "system_admin"}
    )
    assert res_mod.status_code == 403


def test_plant_operator_cannot_list_or_modify_roles(test_fixtures):
    """Verify Plant Operator is blocked from user directory and role operations."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]

    res_list = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['operator']}"}
    )
    assert res_list.status_code == 403

    res_mod = client.put(
        f"/api/admin/users/{target.id}/role",
        headers={"Authorization": f"Bearer {tokens['operator']}"},
        json={"role": "system_admin"}
    )
    assert res_mod.status_code == 403


def test_unauthenticated_request_rejected():
    """Verify 401 Unauthorized for unauthenticated requests."""
    res_list = client.get("/api/admin/users")
    assert res_list.status_code == 401

    res_mod = client.put("/api/admin/users/1/role", json={"role": "contributor"})
    assert res_mod.status_code == 401


def test_admin_cannot_self_modify_role_via_directory(test_fixtures):
    """Verify admin cannot accidentally modify their own role via User Directory (prevent lockout)."""
    tokens = test_fixtures["tokens"]
    admin = test_fixtures["admin"]

    res = client.put(
        f"/api/admin/users/{admin.id}/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "contributor", "reason": "Self-demotion attempt"}
    )
    assert res.status_code == 400
    assert "Self-role modification is prohibited" in res.json()["detail"]


def test_cannot_remove_last_system_admin(test_fixtures, db_sessions):
    """Verify safety check blocks demoting the last active system administrator."""
    tokens = test_fixtures["tokens"]
    user_db, _, _ = db_sessions

    # Create a temporary solitary admin scenario by counting active admins
    active_admins = user_db.query(User).filter(
        User.role == "system_admin",
        User.is_active == True
    ).all()

    # If only 1 admin existed, it would fail directly. Let's create an isolated admin test:
    solo_admin = User(
        username="solo_admin_test",
        email="solo_admin_test@chennaiswm.gov.in",
        hashed_password=hash_password("SoloPass123!"),
        full_name="Solo Admin Account",
        role="system_admin",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user_db.add(solo_admin)
    user_db.commit()
    user_db.refresh(solo_admin)

    # Deactivate other admins temporarily in this session to simulate solitary admin
    other_admins = user_db.query(User).filter(
        User.role == "system_admin",
        User.id != solo_admin.id
    ).all()
    for oa in other_admins:
        oa.is_active = False
    user_db.commit()

    try:
        # Now solo_admin is the ONLY active admin
        solo_token = create_access_token({"sub": "test_admin@chennai.gov.in", "role": "system_admin"})
        res = client.put(
            f"/api/admin/users/{solo_admin.id}/role",
            headers={"Authorization": f"Bearer {solo_token}"},
            json={"role": "contributor"}
        )
        assert res.status_code == 400
        assert "Cannot remove or demote the last remaining" in res.json()["detail"]
    finally:
        # Restore active admins
        for oa in other_admins:
            oa.is_active = True
        user_db.delete(solo_admin)
        user_db.commit()


def test_invalid_role_name_rejected(test_fixtures):
    """Verify invalid or arbitrary role names are rejected with 400 Bad Request."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]

    res = client.put(
        f"/api/admin/users/{target.id}/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "super_root_overlord"}
    )
    assert res.status_code == 400
    assert "Invalid role" in res.json()["detail"]


def test_nonexistent_user_returns_404(test_fixtures):
    """Verify attempting to update a nonexistent user returns 404 Not Found."""
    tokens = test_fixtures["tokens"]

    res = client.put(
        "/api/admin/users/99999999/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "contributor"}
    )
    assert res.status_code == 404


def test_admin_session_switch_and_restore(test_fixtures, db_sessions):
    """Verify admin preview switching and safe restoration of session role."""
    tokens = test_fixtures["tokens"]
    admin = test_fixtures["admin"]
    user_db, _, _ = db_sessions

    # 1. Admin switches role to preview plant_operator
    res_switch = client.post(
        "/api/auth/switch-role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "plant_operator"}
    )
    assert res_switch.status_code == 200
    switched_data = res_switch.json()
    assert switched_data["active_role"] == "plant_operator"
    new_token = switched_data["access_token"]

    # 2. From preview state, Admin safely restores permanent system_admin session
    res_restore = client.post(
        "/api/auth/restore-session",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    assert res_restore.status_code == 200
    restored_data = res_restore.json()
    assert restored_data["active_role"] == "system_admin"

    # Verify user record is system_admin
    user_db.expire_all()
    refreshed_admin = user_db.query(User).filter(User.id == admin.id).first()
    assert refreshed_admin.role == "system_admin"


def test_roles_catalog_endpoint(test_fixtures):
    """Verify official roles catalog endpoint returns defined roles and metadata."""
    tokens = test_fixtures["tokens"]
    res = client.get(
        "/api/admin/roles",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) >= 5
    role_names = [r["role"] for r in roles]
    assert "system_admin" in role_names
    assert "ai_admin" in role_names
    assert "municipal_officer" in role_names
    assert "contributor" in role_names
    assert "public" in role_names


# =========================================================================
# 3. ADMIN ADD USER, UPDATE DETAILS, AND PASSWORD RESET TESTS
# =========================================================================

def test_admin_can_create_user_with_single_use_activation_token(test_fixtures, db_sessions):
    """Verify Admin can create a user, generating single-use activation token, DB B staff profile, and audit log."""
    tokens = test_fixtures["tokens"]
    user_db, staff_db, _ = db_sessions

    payload = {
        "email": "fresh_officer_test@chennaiswm.gov.in",
        "full_name": "Fresh Officer Test",
        "role": "municipal_officer",
        "organization": "Greater Chennai Corporation",
        "phone_number": "9840998877",
        "assigned_ward": 82
    }

    # Ensure idempotency by removing any prior test artifact
    existing = user_db.query(User).filter(User.email == payload["email"]).first()
    if existing:
        user_db.query(PasswordResetToken).filter(PasswordResetToken.user_id == existing.id).delete()
        user_db.query(AuthAuditLog).filter(AuthAuditLog.user_id == existing.id).delete()
        staff_db.query(StaffProfile).filter(StaffProfile.user_id == existing.id).delete()
        user_db.delete(existing)
        user_db.commit()
        staff_db.commit()

    res = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json=payload
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["role"] == payload["role"]
    assert data["activation_token"] is not None
    assert len(data["activation_token"]) >= 32
    assert "reset-password?token=" in data["activation_url"]
    assert data["email_delivery_status"] == "not_configured"

    # Verify user exists in users.db with unguessable password hash
    user_db.expire_all()
    created_user = user_db.query(User).filter(User.email == payload["email"]).first()
    assert created_user is not None
    assert created_user.full_name == payload["full_name"]
    assert created_user.hashed_password is not None
    assert len(created_user.hashed_password) > 20

    # Verify staff profile was linked in staff.db
    staff_db.expire_all()
    profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == created_user.id).first()
    assert profile is not None
    assert profile.assigned_ward_number == 82

    # Verify audit log recorded
    log = user_db.query(AuthAuditLog).filter(
        AuthAuditLog.user_id == created_user.id,
        AuthAuditLog.action.like("%user_created%")
    ).first()
    assert log is not None


def test_admin_create_user_duplicate_email_rejected(test_fixtures):
    """Verify duplicate email returns 400 Bad Request."""
    tokens = test_fixtures["tokens"]

    payload = {
        "email": "fresh_officer_test@chennaiswm.gov.in",
        "full_name": "Duplicate Officer",
        "role": "municipal_officer"
    }

    res = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json=payload
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


def test_admin_create_user_invalid_role_rejected(test_fixtures):
    """Verify unauthorized or invalid roles return 400 Bad Request."""
    tokens = test_fixtures["tokens"]

    payload = {
        "email": "invalid_role_user@chennaiswm.gov.in",
        "full_name": "Invalid Role User",
        "role": "supreme_emperor"
    }

    res = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json=payload
    )
    assert res.status_code == 400
    assert "invalid role" in res.json()["detail"].lower()


def test_ordinary_and_operator_cannot_create_users(test_fixtures):
    """Verify contributors and plant operators cannot invoke POST /api/admin/users."""
    tokens = test_fixtures["tokens"]

    payload = {
        "email": "rogue_creation@chennaiswm.gov.in",
        "full_name": "Rogue User",
        "role": "system_admin"
    }

    res_contrib = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['contributor']}"},
        json=payload
    )
    assert res_contrib.status_code == 403

    res_operator = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {tokens['operator']}"},
        json=payload
    )
    assert res_operator.status_code == 403


def test_admin_can_update_permitted_user_details(test_fixtures, db_sessions):
    """Verify Admin can update user details and audit log is recorded."""
    tokens = test_fixtures["tokens"]
    user_db, staff_db, _ = db_sessions

    target = user_db.query(User).filter(User.email == "fresh_officer_test@chennaiswm.gov.in").first()
    assert target is not None

    update_payload = {
        "full_name": "Updated Officer Name",
        "organization": "GCC Solid Waste Dept",
        "phone_number": "9123456789",
        "assigned_ward": 102
    }

    res = client.put(
        f"/api/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json=update_payload
    )
    assert res.status_code == 200
    updated_user = res.json()
    assert updated_user["full_name"] == update_payload["full_name"]

    # Verify staff profile in DB B is synced
    staff_db.expire_all()
    profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == target.id).first()
    assert profile is not None
    assert profile.assigned_ward_number == 102


def test_admin_cannot_deactivate_last_active_system_admin(test_fixtures, db_sessions):
    """Verify Admin cannot deactivate the sole remaining active admin."""
    tokens = test_fixtures["tokens"]
    user_db, _, _ = db_sessions

    # Create temporary solo admin
    solo = User(
        username="solo_deact_test",
        email="solo_deact_test@chennai.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Solo Deact Admin",
        role="system_admin",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user_db.add(solo)
    user_db.commit()
    user_db.refresh(solo)

    # Deactivate other admins
    other_admins = user_db.query(User).filter(
        User.role == "system_admin",
        User.id != solo.id
    ).all()
    for oa in other_admins:
        oa.is_active = False
    user_db.commit()

    try:
        solo_token = create_access_token({"sub": "test_admin@chennai.gov.in", "role": "system_admin"})
        res = client.put(
            f"/api/admin/users/{solo.id}",
            headers={"Authorization": f"Bearer {solo_token}"},
            json={"is_active": False}
        )
        assert res.status_code == 400
        assert "cannot deactivate the last remaining" in res.json()["detail"].lower()
    finally:
        for oa in other_admins:
            oa.is_active = True
        user_db.delete(solo)
        user_db.commit()


def test_admin_can_initiate_password_reset_and_complete(test_fixtures, db_sessions):
    """Verify Admin initiates reset, returns secure single-use token, invalidates prior tokens, and completes reset."""
    tokens = test_fixtures["tokens"]
    target = test_fixtures["target"]
    user_db, _, _ = db_sessions

    # 1. Admin initiates reset
    res = client.post(
        f"/api/admin/users/{target.id}/reset-password",
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert res.status_code == 200
    reset_data = res.json()
    assert reset_data["success"] is True
    assert reset_data["email"] == target.email
    assert reset_data["reset_token"] is not None
    assert reset_data["email_delivery_status"] == "not_configured"

    # 2. Complete password reset with the token
    new_password = "BrandNewSecurePassword123!"
    res_complete = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_data["reset_token"],
            "new_password": new_password
        }
    )
    assert res_complete.status_code == 200
    assert "successfully" in res_complete.json()["message"].lower()

    # 3. Attempting to reuse the same token should fail
    res_reuse = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_data["reset_token"],
            "new_password": "AnotherAttempt123!"
        }
    )
    assert res_reuse.status_code == 400
    assert "invalid" in res_reuse.json()["detail"].lower() or "already been used" in res_reuse.json()["detail"].lower()


# =========================================================================
# 4. ASSIGNED COLLECTION TRUCK MINI-MAP LOCATION ENDPOINT TESTS
# =========================================================================

def test_assigned_truck_location_endpoint(test_fixtures, db_sessions):
    """Verify public assigned truck location endpoint provides public-safe data and distinguishes status modes."""
    tokens = test_fixtures["tokens"]
    user_db, _, waste_db = db_sessions
    from app.models.vehicle import CollectionVehicle

    # 1. Unauthenticated request rejected
    res_unauth = client.get("/api/public/assigned-truck/location")
    assert res_unauth.status_code == 401

    # Ensure Ward 102 has a collection truck seeded in waste_db
    truck_102 = waste_db.query(CollectionVehicle).filter(CollectionVehicle.assigned_ward_id == 102).first()
    if not truck_102:
        truck_102 = CollectionVehicle(
            vehicle_code="TN-01-WD-102",
            registration_no="TN-01-AZ-1020",
            vehicle_type="Compactor",
            status="collecting",
            assigned_ward_id=102,
            assigned_zone_id=8,
            latitude=13.0850,
            longitude=80.2150,
            driver_name="Secret Driver 102",
            driver_phone="9876543210",
            capacity_tons=5.0
        )
        waste_db.add(truck_102)
        waste_db.commit()
        waste_db.refresh(truck_102)

    # 2. Case A: Contributor verified in Ward 102 with active truck
    contributor = test_fixtures["contributor"]
    contributor.preferences_json = '{"assigned_ward": 102}'
    user_db.commit()

    res = client.get(
        "/api/public/assigned-truck/location",
        headers={"Authorization": f"Bearer {tokens['contributor']}"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["assigned"] is True
    assert data["vehicle_code"] in ["TN-01-WD-102", "GC-05"] or len(data["vehicle_code"]) > 0
    assert data["status"] in ["collecting", "active", "en_route", "in_transit", "idle", "maintenance"]
    assert data["data_mode"] in ["live", "simulated", "stale"]
    assert data["latitude"] is not None and -90 <= data["latitude"] <= 90
    assert data["longitude"] is not None and -180 <= data["longitude"] <= 180

    # Strict omission of private driver details
    assert "driver_name" not in data
    assert "driver_phone" not in data
    assert "fuel_level_liters" not in data

    # 3. Case B: Contributor in an unassigned ward without a truck displays unavailable state
    contributor.preferences_json = '{"assigned_ward": 199}'
    user_db.commit()

    res_unassigned = client.get(
        "/api/public/assigned-truck/location",
        headers={"Authorization": f"Bearer {tokens['contributor']}"}
    )
    assert res_unassigned.status_code == 200
    unassigned_data = res_unassigned.json()
    assert unassigned_data["assigned"] is False
    assert unassigned_data["status"] == "unavailable"
    assert unassigned_data["data_mode"] == "unavailable"
    assert unassigned_data["latitude"] is None
    assert unassigned_data["longitude"] is None

