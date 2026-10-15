import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.database import UserSessionLocal, StaffSessionLocal, WasteSessionLocal
from app.models.user import User, AuthAuditLog
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
