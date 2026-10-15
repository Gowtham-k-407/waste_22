import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.database import UserSessionLocal, StaffSessionLocal, WasteSessionLocal
from app.models.user import User
from app.models.staff import StaffProfile
from app.models.complaint import PublicComplaint, ComplaintFollowUp, GCC_ESCALATION_HIERARCHY
from app.models.vehicle import CollectionVehicle

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
def test_setup(db_sessions):
    user_db, staff_db, waste_db = db_sessions

    # 1. Resident A (Ward 102)
    resident_a = user_db.query(User).filter(User.email == "resident_a@chennaicivic.in").first()
    if not resident_a:
        resident_a = User(
            username="resident_a",
            email="resident_a@chennaicivic.in",
            hashed_password=hash_password("CitizenPass123!"),
            full_name="Priya resident A",
            role="contributor",
            is_active=True,
            preferences_json='{"assigned_ward": 102, "neighborhood": "Anna Nagar East"}',
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(resident_a)
        user_db.commit()
        user_db.refresh(resident_a)
    else:
        resident_a.preferences_json = '{"assigned_ward": 102, "neighborhood": "Anna Nagar East"}'
        user_db.commit()

    # 2. Resident B (Ward 82)
    resident_b = user_db.query(User).filter(User.email == "resident_b@chennaicivic.in").first()
    if not resident_b:
        resident_b = User(
            username="resident_b",
            email="resident_b@chennaicivic.in",
            hashed_password=hash_password("CitizenPass123!"),
            full_name="Sundar resident B",
            role="contributor",
            is_active=True,
            preferences_json='{"assigned_ward": 82, "neighborhood": "Thiruvanmiyur"}',
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(resident_b)
        user_db.commit()
        user_db.refresh(resident_b)
    else:
        resident_b.preferences_json = '{"assigned_ward": 82, "neighborhood": "Thiruvanmiyur"}'
        user_db.commit()

    # 3. Municipal Staff (Assistant Engineer, Ward 82)
    staff_user = user_db.query(User).filter(User.email == "ae_test_82@chennai.gov.in").first()
    if not staff_user:
        staff_user = User(
            username="ae_test_82",
            email="ae_test_82@chennai.gov.in",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Karthik AE Ward 82",
            role="assistant_engineer",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(staff_user)
        user_db.commit()
        user_db.refresh(staff_user)

    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == staff_user.id).first()
    if not staff_profile:
        staff_profile = StaffProfile(
            user_id=staff_user.id,
            employee_id="GCC-TEST-8299",
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

    # 4. System Admin
    admin = user_db.query(User).filter(User.email == "sys_admin_test@chennai.gov.in").first()
    if not admin:
        admin = User(
            username="sys_admin_test",
            email="sys_admin_test@chennai.gov.in",
            hashed_password=hash_password("AdminPass123!"),
            full_name="System Admin Test",
            role="system_admin",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(admin)
        user_db.commit()
        user_db.refresh(admin)

    # 5. Seed collection truck for Ward 102 and Ward 82 if needed
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

    tokens = {
        "resident_a": create_access_token({"sub": resident_a.email, "role": resident_a.role}),
        "resident_b": create_access_token({"sub": resident_b.email, "role": resident_b.role}),
        "staff": create_access_token({"sub": staff_user.email, "role": staff_user.role}),
        "admin": create_access_token({"sub": admin.email, "role": admin.role})
    }

    return {
        "resident_a": resident_a,
        "resident_b": resident_b,
        "staff": staff_user,
        "admin": admin,
        "tokens": tokens,
        "truck_102": truck_102
    }


# =========================================================================
# 1. Public Dashboard Tests
# =========================================================================

def test_unauthenticated_dashboard_rejected():
    """Unauthenticated access to public dashboard must return 401."""
    res = client.get("/api/public/dashboard")
    assert res.status_code == 401


def test_resident_accesses_permitted_dashboard(test_setup):
    """A verified resident can access their public neighborhood dashboard."""
    token = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/public/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["verified_ward"] == 102
    assert "collection_schedule" in data
    assert "assigned_truck" in data
    assert "public_metrics" in data
    assert "my_grievances" in data
    assert isinstance(data["my_grievances"], list)


def test_resident_cannot_access_staff_and_admin_endpoints(test_setup):
    """Direct API calls from public resident to staff/admin endpoints return 403."""
    token = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_endpoints = [
        ("GET", "/api/admin/overview"),
        ("GET", "/api/admin/uploads"),
        ("GET", "/api/admin/dataset"),
        ("GET", "/api/admin/models"),
        ("GET", "/api/admin/training-status"),
        ("GET", "/api/plants/"),
        ("GET", "/api/optimization/recommendations"),
        ("GET", "/api/alerts/"),
        ("POST", "/api/alerts/1/resolve"),
        ("POST", "/api/simulation/start"),
    ]

    for method, ep in forbidden_endpoints:
        if method == "GET":
            r = client.get(ep, headers=headers)
        else:
            r = client.post(ep, json={}, headers=headers)
        assert r.status_code == 403, f"Expected 403 for {method} {ep}, got {r.status_code}"


# =========================================================================
# 2. Truck Status & Fleet Privacy Tests
# =========================================================================

def test_resident_gets_assigned_truck_with_public_fields_only(test_setup):
    """Resident can view assigned truck, strictly excluding driver phone and telemetry."""
    token = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/vehicles/assigned-truck", headers=headers)
    assert res.status_code == 200
    truck = res.json()

    assert truck["assigned_ward_number"] == 102
    assert "vehicle_code" in truck
    assert "status" in truck
    assert "data_mode" in truck
    assert truck["data_mode"] in ["live", "simulated", "stale", "unavailable"]

    # Sensitive fields MUST NOT be exposed to public users
    assert "driver_name" not in truck
    assert "driver_phone" not in truck
    assert "fuel_level_liters" not in truck
    assert "fuel_type" not in truck


def test_public_user_cannot_access_full_fleet_endpoint(test_setup):
    """Public resident cannot access the full city-wide vehicle telemetry stream."""
    token = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/vehicles/", headers=headers)
    assert res.status_code == 403


def test_staff_and_admin_can_access_full_fleet(test_setup):
    """Municipal staff and admin retain access to full fleet data."""
    staff_token = test_setup["tokens"]["staff"]
    admin_token = test_setup["tokens"]["admin"]

    res_staff = client.get("/api/vehicles/", headers={"Authorization": f"Bearer {staff_token}"})
    assert res_staff.status_code == 200

    res_admin = client.get("/api/vehicles/", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200


def test_resident_cannot_inspect_other_ward_truck_via_vehicle_code(test_setup):
    """
    Public user attempting to inspect a truck outside their assigned ward
    receives 404 Not Found (IDOR and resource enumeration protection).
    """
    # Resident B is in Ward 82. Ward 102 truck should return 404 for Resident B.
    token_b = test_setup["tokens"]["resident_b"]
    headers = {"Authorization": f"Bearer {token_b}"}

    truck_102 = test_setup["truck_102"]
    res = client.get(f"/api/vehicles/{truck_102.vehicle_code}", headers=headers)
    assert res.status_code == 404


# =========================================================================
# 3. Sanitation Issue Reporting Tests
# =========================================================================

def test_resident_can_submit_valid_grievance(test_setup):
    """Resident submits a sanitary civic report, server enforces ownership and initial status."""
    token_a = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    payload = {
        "title": "Overflowing Garbage Bin near 2nd Avenue",
        "description": "Public bin has been overflowing for 24 hours spilling onto pedestrian pavement.",
        "category": "overflowing_bin",
        "priority": "high",
        "location_address": "2nd Avenue, Anna Nagar East",
        "ward_id": 102,
        # Attempt mass assignment tampering
        "status": "resolved",
        "citizen_user_id": 9999
    }

    res = client.post("/api/complaints", json=payload, headers=headers)
    assert res.status_code == 201
    complaint = res.json()

    assert complaint["title"] == payload["title"]
    assert complaint["category"] == "overflowing_bin"
    # Verify mass assignment was rejected: status must be submitted, not resolved
    assert complaint["status"] == "submitted"
    assert complaint["tracking_number"].startswith("GCC-")
    assert complaint["citizen_user_id"] == test_setup["resident_a"].id


def test_invalid_category_rejected():
    """Unsupported civic categories are rejected with 422."""
    from app.core.security import create_access_token
    token = create_access_token({"sub": "resident_a@chennaicivic.in", "role": "contributor"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Unsupported Issue",
        "description": "Some description",
        "category": "unsupported_foreign_category",
        "location_address": "Some street"
    }
    res = client.post("/api/complaints", json=payload, headers=headers)
    assert res.status_code in [400, 422]


# =========================================================================
# 4. Grievance Tracking & IDOR Protection Tests
# =========================================================================

def test_resident_sees_only_own_grievances(test_setup):
    """Grievance list endpoint filters strictly by authenticated user ownership."""
    token_a = test_setup["tokens"]["resident_a"]
    token_b = test_setup["tokens"]["resident_b"]

    # Resident B submits a complaint
    res_b_create = client.post("/api/complaints", json={
        "title": "Drainage Blockage at Ward 82",
        "description": "Sewage and plastic waste blocking storm drain.",
        "category": "drainage_blockage",
        "priority": "medium",
        "location_address": "Beach Road, Thiruvanmiyur",
        "ward_id": 82
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_create.status_code == 201
    complaint_b = res_b_create.json()

    # Resident A fetches grievances
    res_a_list = client.get("/api/complaints", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a_list.status_code == 200
    res_data = res_a_list.json()
    complaints_a = res_data.get("complaints", res_data) if isinstance(res_data, dict) else res_data

    # Verify Resident B's complaint is NOT in Resident A's list
    b_ids = [c["id"] for c in complaints_a]
    assert complaint_b["id"] not in b_ids

    # Resident A attempting to access Resident B's complaint directly gets 404 (IDOR protection)
    res_idor = client.get(f"/api/complaints/{complaint_b['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_idor.status_code == 404


def test_resident_cannot_follow_up_on_another_users_grievance(test_setup):
    """A resident cannot post follow-up comments on another resident's grievance."""
    token_a = test_setup["tokens"]["resident_a"]
    token_b = test_setup["tokens"]["resident_b"]

    # Resident B creates complaint
    res_create = client.post("/api/complaints", json={
        "title": "Illegal Dumping on Street Corner",
        "description": "Debris dumped overnight.",
        "category": "illegal_dumping",
        "location_address": "East Coast Road",
        "ward_id": 82
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert res_create.status_code == 201
    comp_id = res_create.json()["id"]

    # Resident A attempts to follow up
    res_follow = client.post(f"/api/complaints/{comp_id}/follow-up", json={
        "message": "Tampering attempt from Resident A"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert res_follow.status_code == 404


def test_resident_can_follow_up_on_own_grievance(test_setup):
    """A resident can successfully add follow-up information to their own grievance."""
    token_b = test_setup["tokens"]["resident_b"]

    # Resident B creates complaint
    res_create = client.post("/api/complaints", json={
        "title": "Public Dustbin Damaged",
        "description": "Lid broken and waste exposed.",
        "category": "damaged_bin",
        "location_address": "Lattice Bridge Road",
        "ward_id": 82
    }, headers={"Authorization": f"Bearer {token_b}"})
    comp_id = res_create.json()["id"]

    # Resident B follows up
    res_follow = client.post(f"/api/complaints/{comp_id}/follow-up", json={
        "message": "Waste is now attracting stray animals, please expedite."
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert res_follow.status_code in [200, 201]
    data = res_follow.json()
    assert data["success"] is True
    assert "timeline" in data["message"].lower() or "follow-up" in data["message"].lower()


# =========================================================================
# 5. Privileged Action Prevention
# =========================================================================

def test_resident_cannot_directly_change_complaint_status(test_setup):
    """Residents cannot mark grievances as Resolved, Closed, or In-Progress."""
    token_b = test_setup["tokens"]["resident_b"]

    res_create = client.post("/api/complaints", json={
        "title": "Missed Collection Morning Route",
        "description": "Truck did not arrive today.",
        "category": "missed_collection",
        "location_address": "South Mada Street",
        "ward_id": 82
    }, headers={"Authorization": f"Bearer {token_b}"})
    comp_id = res_create.json()["id"]

    # Citizen tries to mark it resolved
    res_status = client.post(f"/api/complaints/{comp_id}/status", json={
        "new_status": "resolved",
        "notes": "Citizen trying to self-resolve"
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert res_status.status_code == 403


# =========================================================================
# 6. Multi-Tier Municipal Escalation Policy Tests
# =========================================================================

def test_resident_cannot_escalate_another_users_grievance(test_setup):
    """Resident A attempting to escalate Resident B's grievance receives 404."""
    token_a = test_setup["tokens"]["resident_a"]
    token_b = test_setup["tokens"]["resident_b"]

    res_create = client.post("/api/complaints", json={
        "title": "Littering in Public Park",
        "description": "Plastic bottles scattered in park.",
        "category": "street_cleaning",
        "location_address": "Park Road",
        "ward_id": 82
    }, headers={"Authorization": f"Bearer {token_b}"})
    comp_id = res_create.json()["id"]

    res_esc = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "Unauthorized escalation attempt"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert res_esc.status_code == 404


def test_multi_tier_escalation_workflow(test_setup):
    """
    Resident can escalate their own grievance up the GCC hierarchy:
    Tier 0 (Ward Sanitary Inspector) ->
    Tier 1 (Assistant Engineer / Zonal Officer) ->
    Tier 2 (Municipal Health Officer) ->
    Tier 3 (Municipal Commissioner Executive Cell)
    Cannot escalate beyond Tier 3.
    """
    token_a = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    # 1. Create Complaint (starts at Tier 0)
    res_create = client.post("/api/complaints", json={
        "title": "Severe Stagnant Drainage and Mosquito Breeding",
        "description": "Drain overflowing for 3 days without municipal response.",
        "category": "drainage_blockage",
        "priority": "critical",
        "location_address": "10th Main Road, Anna Nagar",
        "ward_id": 102
    }, headers=headers)
    assert res_create.status_code == 201
    comp_id = res_create.json()["id"]

    # 2. First Escalation -> Tier 1
    res_esc1 = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "Overdue resolution at ward level"
    }, headers=headers)
    assert res_esc1.status_code == 200
    esc1_data = res_esc1.json()
    assert esc1_data["escalation_level"] == 1
    assert "Assistant Engineer" in esc1_data["assigned_authority_role"] or "Zonal Officer" in esc1_data["assigned_authority_role"]

    # 3. Second Escalation -> Tier 2
    res_esc2 = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "No response from Assistant Engineer"
    }, headers=headers)
    assert res_esc2.status_code == 200
    esc2_data = res_esc2.json()
    assert esc2_data["escalation_level"] == 2
    assert "Municipal Health Officer" in esc2_data["assigned_authority_role"]

    # 4. Third Escalation -> Tier 3
    res_esc3 = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "Critical public health hazard requires Commissioner attention"
    }, headers=headers)
    assert res_esc3.status_code == 200
    esc3_data = res_esc3.json()
    assert esc3_data["escalation_level"] == 3
    assert "Municipal Commissioner" in esc3_data["assigned_authority_role"]

    # 5. Fourth Escalation -> Rejected (Ceiling Reached)
    res_esc4 = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "Attempt to escalate beyond maximum tier"
    }, headers=headers)
    assert res_esc4.status_code == 400
    assert "highest municipal authority" in res_esc4.json()["detail"].lower()


def test_cannot_escalate_resolved_complaint(test_setup, db_sessions):
    """Complaints already marked resolved cannot be escalated."""
    _, _, waste_db = db_sessions
    token_a = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    res_create = client.post("/api/complaints", json={
        "title": "Minor Roadside Debris",
        "description": "Small pile of leaves.",
        "category": "street_cleaning",
        "location_address": "6th Avenue",
        "ward_id": 102
    }, headers=headers)
    comp_id = res_create.json()["id"]

    # Municipal staff / system marks it resolved in DB
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == comp_id).first()
    complaint.status = "resolved"
    waste_db.commit()

    # Citizen tries to escalate
    res_esc = client.post(f"/api/complaints/{comp_id}/escalate", json={
        "reason": "Trying to escalate resolved complaint"
    }, headers=headers)
    assert res_esc.status_code == 400
    assert "cannot escalate an already resolved" in res_esc.json()["detail"].lower()


def test_resident_can_reopen_resolved_complaint(test_setup, db_sessions):
    """Resident can reopen an improperly resolved grievance with a reason."""
    _, _, waste_db = db_sessions
    token_a = test_setup["tokens"]["resident_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    res_create = client.post("/api/complaints", json={
        "title": "Garbage Truck Spillage",
        "description": "Truck spilled waste while compacting.",
        "category": "missed_collection",
        "location_address": "8th Avenue",
        "ward_id": 102
    }, headers=headers)
    comp_id = res_create.json()["id"]

    # Mark resolved in DB
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == comp_id).first()
    complaint.status = "resolved"
    waste_db.commit()

    # Resident reopens
    res_reopen = client.post(f"/api/complaints/{comp_id}/reopen", json={
        "reason": "Spilled waste was only partially cleaned, glass shards remain on pavement."
    }, headers=headers)
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "reopened"
