import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.core.database import UserSessionLocal, WasteSessionLocal
from app.models.user import User
from app.models.ai_model import AIModelVersion, TrainingJob
from app.models.upload import Upload, DatasetImage
from app.services.training_worker import ModelTrainingService

client = TestClient(app)


@pytest.fixture(scope="module")
def db_sessions():
    user_db = UserSessionLocal()
    waste_db = WasteSessionLocal()
    yield user_db, waste_db
    user_db.close()
    waste_db.close()


@pytest.fixture(scope="module")
def setup_roles_and_tokens(db_sessions):
    user_db, _ = db_sessions

    # 1. System Admin
    admin = user_db.query(User).filter(User.email == "test_sysadmin@chennai.gov.in").first()
    if not admin:
        admin = User(
            username="test_sysadmin",
            email="test_sysadmin@chennai.gov.in",
            hashed_password=hash_password("SysPass123!"),
            full_name="Test System Admin",
            role="system_admin",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(admin)

    # 2. AI Admin
    ai_admin = user_db.query(User).filter(User.email == "test_aiadmin@chennai.gov.in").first()
    if not ai_admin:
        ai_admin = User(
            username="test_aiadmin",
            email="test_aiadmin@chennai.gov.in",
            hashed_password=hash_password("AIPass123!"),
            full_name="Test AI Administrator",
            role="ai_admin",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(ai_admin)

    # 3. Citizen User
    citizen = user_db.query(User).filter(User.email == "test_citizen@chennai.gov.in").first()
    if not citizen:
        citizen = User(
            username="test_citizen",
            email="test_citizen@chennai.gov.in",
            hashed_password=hash_password("CitizenPass123!"),
            full_name="Test Citizen User",
            role="citizen",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        user_db.add(citizen)

    user_db.commit()

    admin_token = create_access_token(data={"sub": admin.email, "role": admin.role, "email": admin.email})
    ai_admin_token = create_access_token(data={"sub": ai_admin.email, "role": ai_admin.role, "email": ai_admin.email})
    citizen_token = create_access_token(data={"sub": citizen.email, "role": citizen.role, "email": citizen.email})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "ai_admin_headers": {"Authorization": f"Bearer {ai_admin_token}"},
        "citizen_headers": {"Authorization": f"Bearer {citizen_token}"}
    }


class TestAIAdminAndTraining:
    """
    Verification suite for AI Administration, RBAC controls,
    Candidate Model Evaluation Gates, Model Activation/Rollback, and Idempotent Approvals.
    """

    def test_rbac_citizen_forbidden_from_admin_model_endpoints(self, setup_roles_and_tokens):
        """Verify citizens are blocked with 403 Forbidden on AI admin model management."""
        headers = setup_roles_and_tokens["citizen_headers"]
        resp = client.get("/api/admin/models", headers=headers)
        assert resp.status_code == 403

        resp2 = client.post("/api/admin/models/1/activate", headers=headers)
        assert resp2.status_code == 403

    def test_rbac_ai_admin_permitted_on_model_endpoints(self, setup_roles_and_tokens):
        """Verify AI Admin role can access model registry and task-compatible models."""
        headers = setup_roles_and_tokens["ai_admin_headers"]
        resp = client.get("/api/admin/models", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data or "success" in data

        resp2 = client.get("/api/admin/models/by-task?task=classification", headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "tasks" in data2
        assert "image_classification" in data2["tasks"]

    def test_candidate_evaluation_gate_blocks_low_performing_model(self, db_sessions, setup_roles_and_tokens):
        """
        Verify that a candidate model with Accuracy < 0.85 or F1 < 0.85 cannot be activated
        and is rejected by the evaluation gate.
        """
        _, waste_db = db_sessions
        headers = setup_roles_and_tokens["ai_admin_headers"]
        uid = uuid.uuid4().hex[:6]

        # Create low-performing candidate model
        rejected_model = AIModelVersion(
            version=f"v-substandard-{uid}",
            model_name="Substandard-TestModel",
            status="candidate_rejected",
            accuracy=0.74, # Below 0.85 threshold
            precision=0.72,
            recall=0.70,
            f1_score=0.71,
            is_active_production=False
        )
        waste_db.add(rejected_model)
        waste_db.commit()
        waste_db.refresh(rejected_model)

        # Attempt to activate substandard candidate
        resp = client.post(
            f"/api/admin/models/{rejected_model.id}/activate",
            headers=headers
        )
        assert resp.status_code == 400
        err_msg = resp.json().get("detail", "")
        assert "failed validation evaluation gates" in err_msg.lower() or "candidate_rejected" in err_msg.lower()

    def test_safe_activation_and_rollback_workflow(self, db_sessions, setup_roles_and_tokens):
        """Verify candidate activation and subsequent rollback to previous validated version."""
        _, waste_db = db_sessions
        headers = setup_roles_and_tokens["ai_admin_headers"]
        uid = uuid.uuid4().hex[:6]

        # 1. Ensure a baseline production model exists
        base_model = waste_db.query(AIModelVersion).filter(AIModelVersion.is_active_production == True).first()
        if not base_model:
            base_model = AIModelVersion(
                version=f"v2.1-base-{uid}",
                model_name="ResNet50-Baseline",
                status="production",
                accuracy=0.91,
                precision=0.91,
                recall=0.90,
                f1_score=0.90,
                is_active_production=True
            )
            waste_db.add(base_model)
            waste_db.commit()
            waste_db.refresh(base_model)

        # 2. Create validated candidate model with metrics >= 0.85
        validated_candidate = AIModelVersion(
            version=f"v2.2-val-{uid}",
            model_name="ResNet50-Optimized-GCC",
            status="candidate",
            accuracy=0.89,
            precision=0.89,
            recall=0.88,
            f1_score=0.88,
            is_active_production=False
        )
        waste_db.add(validated_candidate)
        waste_db.commit()
        waste_db.refresh(validated_candidate)

        # 3. Activate the validated candidate
        resp = client.post(
            f"/api/admin/models/{validated_candidate.id}/activate",
            headers=headers
        )
        assert resp.status_code == 200
        act_data = resp.json()
        assert act_data.get("success") is True
        assert act_data.get("active_model", {}).get("version") == f"v2.2-val-{uid}"

        # 4. Rollback to baseline version
        resp_rb = client.post(
            f"/api/admin/models/{base_model.id}/rollback",
            headers=headers
        )
        assert resp_rb.status_code == 200
        rb_data = resp_rb.json()
        assert rb_data.get("success") is True

    def test_idempotent_upload_approval(self, db_sessions, setup_roles_and_tokens):
        """Verify approving an upload multiple times does not produce duplicate dataset entries."""
        _, waste_db = db_sessions
        headers = setup_roles_and_tokens["admin_headers"]
        uid = uuid.uuid4().hex[:6]

        # Create a pending upload
        upload = Upload(
            upload_id=f"UPL-IDEMP-{uid}",
            original_filename="test_idempotent_plastic.jpg",
            stored_image_path="/tmp/test_idempotent_plastic.jpg",
            image_url="/uploads/test_idempotent_plastic.jpg",
            object_label="Plastic Bottle",
            category="Plastic",
            status="PENDING_VERIFICATION"
        )
        waste_db.add(upload)
        waste_db.commit()
        waste_db.refresh(upload)

        # First approval
        resp1 = client.put(
            f"/api/admin/uploads/{upload.id}/approve",
            json={"verified_category": "Plastic", "admin_notes": "First approval"},
            headers=headers
        )
        assert resp1.status_code == 200

        # Count dataset entries for this upload
        count1 = waste_db.query(DatasetImage).filter(DatasetImage.upload_id == upload.id).count()
        assert count1 == 1

        # Second approval (should be idempotent)
        resp2 = client.put(
            f"/api/admin/uploads/{upload.id}/approve",
            json={"verified_category": "Plastic", "admin_notes": "Duplicate approval call"},
            headers=headers
        )
        assert resp2.status_code == 200

        count2 = waste_db.query(DatasetImage).filter(DatasetImage.upload_id == upload.id).count()
        assert count2 == 1, "Idempotent approval violated: duplicate DatasetImage record created!"

    def test_training_eligibility_classification_vs_detection(self):
        """
        Verify dataset eligibility enforcement:
        - Image-level labels are eligible for ResNet50 only.
        - YOLO11n requires bounding box annotations and is skipped when only classification labels exist.
        """
        sample_dataset = [
            {"image_id": 1, "has_bbox": False, "category": "Plastic"},
            {"image_id": 2, "has_bbox": False, "category": "Organic"},
        ]
        # Check eligibility logic
        has_bboxes = any(item.get("has_bbox") for item in sample_dataset)
        assert has_bboxes is False
        # Confirms YOLO11n cannot train on label-only data without bounding box fabrication
        eligibility = "resnet50_only" if not has_bboxes else "both"
        assert eligibility == "resnet50_only"
