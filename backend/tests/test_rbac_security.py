import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.database import UserSessionLocal, StaffSessionLocal, WasteSessionLocal
from app.models.user import User, AuthAuditLog
from app.models.staff import StaffProfile, StaffAuditLog
from app.models.optimization import OperationalAlert
from app.models.upload import Upload
from app.models.facility import SegregationPlant

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
def test_users(db_sessions):
    user_db, staff_db, waste_db = db_sessions

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

    # 2. Ordinary Contributor (Citizen)
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

    # 3. Second Ordinary Contributor (Citizen B for IDOR testing)
    contributor_b = user_db.query(User).filter(User.email == "citizen_b@gmail.com").first()
    if not contributor_b:
        contributor_b = User(
            username="citizen_b",
            email="citizen_b@gmail.com",
            hashed_password=hash_password("CitizenPass123!"),
            full_name="Priya Citizen B",
            role="contributor",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(contributor_b)
        user_db.commit()
        user_db.refresh(contributor_b)

    # 4. Authorized Municipal Staff (Assistant Engineer, Ward 82)
    staff_user = user_db.query(User).filter(User.email == "ae_ward82@chennai.gov.in").first()
    if not staff_user:
        staff_user = User(
            username="ae_ward82",
            email="ae_ward82@chennai.gov.in",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Karthik Assistant Engineer",
            role="assistant_engineer",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(staff_user)
        user_db.commit()
        user_db.refresh(staff_user)

    # Link staff profile in Database B
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == staff_user.id).first()
    if not staff_profile:
        staff_profile = StaffProfile(
            user_id=staff_user.id,
            employee_id="GCC-TEST-8201",
            full_name=staff_user.full_name,
            job_title="Assistant Engineer",
            role_code="assistant_engineer",
            department="Engineering & Maintenance",
            assigned_ward_number=82,
            assigned_ward_id=82,
            assigned_zone_number=6,
            phone_number="9840112233",
            employment_status="Active"
        )
        staff_db.add(staff_profile)
        staff_db.commit()
        staff_db.refresh(staff_profile)

    tokens = {
        "admin": create_access_token({"sub": admin.email, "role": admin.role}),
        "contributor": create_access_token({"sub": contributor.email, "role": contributor.role}),
        "contributor_b": create_access_token({"sub": contributor_b.email, "role": contributor_b.role}),
        "staff": create_access_token({"sub": staff_user.email, "role": staff_user.role}),
    }

    return {
        "admin": admin,
        "contributor": contributor,
        "contributor_b": contributor_b,
        "staff": staff_user,
        "tokens": tokens
    }


# =========================================================================
# 1. OpenCV Startup & Integrity Check
# =========================================================================

def test_opencv_import_and_version():
    """Verify cv2 imports successfully and has expected version in environment."""
    import cv2
    assert hasattr(cv2, "__version__")
    assert cv2.__version__ is not None
    # Ensure core cv2 image processing routines are functional
    import numpy as np
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    assert gray.shape == (100, 100)


def test_backend_application_startup():
    """Verify FastAPI application boots and health check succeeds."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["city"] == "Chennai, Tamil Nadu"


# =========================================================================
# 2. Authentication & Admin Protection (Phase 2 & 5)
# =========================================================================

def test_unauthenticated_admin_routes_return_401():
    """Verify that requests without credentials to any admin route return 401 Unauthorized."""
    endpoints = [
        "/api/admin/overview",
        "/api/admin/uploads",
        "/api/admin/dataset",
        "/api/admin/models",
        "/api/admin/training-status"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 401, f"Expected 401 for unauthenticated {ep}, got {r.status_code}"


def test_invalid_or_tampered_token_rejected():
    """Verify that malformed or tampered Bearer tokens return 401."""
    r = client.get("/api/admin/overview", headers={"Authorization": "Bearer not_a_valid_jwt"})
    assert r.status_code == 401

    r2 = client.get("/api/admin/overview", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.signature"})
    assert r2.status_code == 401


def test_contributor_cannot_access_admin_overview(test_users):
    """Ordinary citizen contributor must be denied access to admin overview (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.get("/api/admin/overview", headers=headers)
    assert r.status_code == 403
    assert "lacks administrative permissions" in r.json().get("detail", "")


def test_contributor_cannot_modify_admin_uploads(test_users):
    """Ordinary user cannot approve or reject uploads (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.put("/api/admin/uploads/1/approve", json={"verified_category": "Plastic"}, headers=headers)
    assert r.status_code == 403

    r2 = client.put("/api/admin/uploads/1/reject", json={"rejection_reason": "Low quality"}, headers=headers)
    assert r2.status_code == 403


def test_admin_can_access_admin_overview(test_users):
    """Authorized system administrator can access admin overview (200)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['admin']}"}
    r = client.get("/api/admin/overview", headers=headers)
    assert r.status_code == 200
    assert r.json()["success"] is True


# =========================================================================
# 3. Privilege Escalation & Role Switching (Phase 8)
# =========================================================================

def test_contributor_cannot_escalate_to_system_admin(test_users):
    """Ordinary user cannot call /api/auth/switch-role to gain system_admin role (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/auth/switch-role", json={"role": "system_admin"}, headers=headers)
    assert r.status_code == 403
    assert "prohibited" in r.json().get("detail", "").lower()


def test_contributor_cannot_escalate_to_staff_role(test_users):
    """Ordinary user cannot self-assign an unassigned staff role (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/auth/switch-role", json={"role": "assistant_engineer"}, headers=headers)
    assert r.status_code == 403


def test_contributor_can_switch_between_public_and_contributor(test_users):
    """Ordinary user can legitimately switch between contributor and public mode."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/auth/switch-role", json={"role": "public"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["active_role"] == "public"
    assert "access_token" in data

    # Switch back to contributor
    new_token = data["access_token"]
    r2 = client.post("/api/auth/switch-role", json={"role": "contributor"}, headers={"Authorization": f"Bearer {new_token}"})
    assert r2.status_code == 200
    assert r2.json()["active_role"] == "contributor"


# =========================================================================
# 4. Alert Viewing and Resolution Authorization (Phase 6)
# =========================================================================

def test_unauthenticated_alert_resolution_rejected():
    """Unauthenticated users cannot resolve alerts (401)."""
    r = client.post("/api/alerts/1/resolve")
    assert r.status_code == 401


def test_contributor_cannot_view_or_resolve_alerts(test_users):
    """Ordinary users cannot view or resolve operational alerts (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}

    # Viewing operational alerts
    r_view = client.get("/api/alerts/", headers=headers)
    assert r_view.status_code == 403

    # Resolving alert
    r_resolve = client.post("/api/alerts/1/resolve", headers=headers)
    assert r_resolve.status_code == 403


def test_authorized_staff_can_resolve_scoped_alert(test_users, db_sessions):
    """Authorized staff (assistant_engineer) can resolve alert within their assigned ward."""
    user_db, staff_db, waste_db = db_sessions

    # Ensure a test alert exists for Ward 82
    test_alert = waste_db.query(OperationalAlert).filter(OperationalAlert.alert_code == "ALT-TEST-W82").first()
    if not test_alert:
        test_alert = OperationalAlert(
            alert_code="ALT-TEST-W82",
            priority="High",
            category="Segregation",
            location_name="Anna Nagar West Ward 82",
            ward_number=82,
            issue="Severe cardboard and plastic cross-contamination detected at conveyor intake",
            recommended_action="Dispatch inspection team and adjust optical sorter calibration",
            status="Active",
            timestamp=datetime.utcnow()
        )
        waste_db.add(test_alert)
        waste_db.commit()
        waste_db.refresh(test_alert)
    else:
        test_alert.status = "Active"
        test_alert.resolved_at = None
        waste_db.commit()

    headers = {"Authorization": f"Bearer {test_users['tokens']['staff']}"}
    r = client.post(f"/api/alerts/{test_alert.id}/resolve", headers=headers)
    assert r.status_code == 200
    res = r.json()
    assert res["success"] is True
    assert res["resolved_by"] == test_users["staff"].email

    # Verify status changed in database
    waste_db.refresh(test_alert)
    assert test_alert.status == "Resolved"
    assert test_alert.resolved_at is not None

    # Verify audit log was recorded in Database A
    audit_entry = user_db.query(AuthAuditLog).filter(
        AuthAuditLog.user_id == test_users["staff"].id,
        AuthAuditLog.action.like("%alert_resolved%")
    ).first()
    assert audit_entry is not None


def test_ward_scoped_staff_cannot_resolve_out_of_scope_alert(test_users, db_sessions):
    """Staff member assigned to Ward 82 cannot resolve alert for Ward 95 (403)."""
    user_db, staff_db, waste_db = db_sessions

    out_of_scope_alert = waste_db.query(OperationalAlert).filter(OperationalAlert.alert_code == "ALT-TEST-W95").first()
    if not out_of_scope_alert:
        out_of_scope_alert = OperationalAlert(
            alert_code="ALT-TEST-W95",
            priority="Critical",
            category="Plant Capacity",
            location_name="T. Nagar Ward 95",
            ward_number=95,
            issue="Smart bin sensor overflow in commercial zone",
            recommended_action="Reroute compactor truck",
            status="Active",
            timestamp=datetime.utcnow()
        )
        waste_db.add(out_of_scope_alert)
        waste_db.commit()
        waste_db.refresh(out_of_scope_alert)
    else:
        out_of_scope_alert.status = "Active"
        waste_db.commit()

    headers = {"Authorization": f"Bearer {test_users['tokens']['staff']}"}
    r = client.post(f"/api/alerts/{out_of_scope_alert.id}/resolve", headers=headers)
    assert r.status_code == 403
    assert "Ward 82" in r.json().get("detail", "")


# =========================================================================
# 5. Protected AI Models, Training, Simulation & Datasets (Phase 5)
# =========================================================================

def test_contributor_cannot_trigger_retraining(test_users):
    """Ordinary user cannot trigger model retraining (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/ai-training/trigger-retraining", data={"force": "true"}, headers=headers)
    assert r.status_code == 403


def test_contributor_cannot_deploy_model(test_users):
    """Ordinary user cannot deploy AI model to production (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/models/deploy", data={"candidate_version": "v2.2"}, headers=headers)
    assert r.status_code == 403


def test_contributor_cannot_rollback_model(test_users):
    """Ordinary user cannot rollback production AI model (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/models/rollback", headers=headers)
    assert r.status_code == 403


def test_contributor_cannot_toggle_simulation(test_users):
    """Ordinary user cannot start, stop, or toggle simulation mode (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.post("/api/simulation/toggle", headers=headers)
    assert r.status_code == 403

    r2 = client.post("/api/simulation/start", headers=headers)
    assert r2.status_code == 403

    r3 = client.post("/api/simulation/stop", headers=headers)
    assert r3.status_code == 403


def test_contributor_cannot_modify_plant_status(test_users):
    """Ordinary user cannot modify industrial plant operating status (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r = client.put("/api/plants/1/status?status=maintenance", headers=headers)
    assert r.status_code == 403


def test_contributor_cannot_upload_dataset_csv(test_users):
    """Ordinary user cannot upload CSVs into datasets catalog (403)."""
    headers = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    files = {"file": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
    r = client.post("/api/datasets/upload-csv", files=files, headers=headers)
    assert r.status_code == 403


# =========================================================================
# 6. Insecure Direct Object Reference (IDOR) & Scope (Phase 9)
# =========================================================================

def test_idor_protection_on_private_user_uploads(test_users, db_sessions):
    """User B cannot access User A's private/unapproved upload metadata (403)."""
    user_db, staff_db, waste_db = db_sessions

    # Create a private pending upload owned by User A
    user_a = test_users["contributor"]
    private_upload = waste_db.query(Upload).filter(Upload.original_filename == "user_a_private.jpg").first()
    if not private_upload:
        private_upload = Upload(
            user_id=user_a.id,
            user_name=user_a.full_name,
            user_email=user_a.email,
            original_filename="user_a_private.jpg",
            stored_image_path="/tmp/user_a_private.jpg",
            image_url="/uploads/user_a_private.jpg",
            file_size_bytes=102400,
            category="Plastic",
            object_label="Plastic Bottle",
            status="PENDING_VERIFICATION",
            admin_notes="Confidential internal notes for moderator",
            created_at=datetime.utcnow()
        )
        waste_db.add(private_upload)
        waste_db.commit()
        waste_db.refresh(private_upload)

    # 1. Unauthenticated request denied
    r_anon = client.get(f"/api/uploads/{private_upload.id}")
    assert r_anon.status_code == 403

    # 2. User B attempt denied
    headers_b = {"Authorization": f"Bearer {test_users['tokens']['contributor_b']}"}
    r_user_b = client.get(f"/api/uploads/{private_upload.id}", headers=headers_b)
    assert r_user_b.status_code == 403
    assert "Access denied" in r_user_b.json().get("detail", "")

    # 3. Owner (User A) allowed access
    headers_a = {"Authorization": f"Bearer {test_users['tokens']['contributor']}"}
    r_user_a = client.get(f"/api/uploads/{private_upload.id}", headers=headers_a)
    assert r_user_a.status_code == 200
    assert r_user_a.json()["original_filename"] == "user_a_private.jpg"

    # 4. Admin allowed access
    headers_admin = {"Authorization": f"Bearer {test_users['tokens']['admin']}"}
    r_admin = client.get(f"/api/uploads/{private_upload.id}", headers=headers_admin)
    assert r_admin.status_code == 200
    assert r_admin.json()["admin_notes"] == "Confidential internal notes for moderator"
