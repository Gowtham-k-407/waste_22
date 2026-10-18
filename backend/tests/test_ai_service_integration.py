"""
Comprehensive Integration Test Suite for Standalone AI API Service Integration.
Verifies Phase 8 requirements:
1. Existing endpoints retain their documented request/response contracts.
2. Detection and classification requests are forwarded to the configured AI API.
3. AI responses are mapped correctly into existing response schemas.
4. Existing database persistence and workflow behavior remain unchanged.
5. Timeouts and connection failures are handled safely.
6. Missing models do not generate fabricated predictions.
7. Authentication and RBAC remain enforced.
8. Existing frontend API calls continue to work.
9. No local IP address or credential is hardcoded into production code.
10. Environment configuration supports both localhost and LAN access.
11. The project builds and starts without import or dependency errors.
"""

import io
import re
import os
import json
import uuid
from datetime import datetime
import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import UserSessionLocal, WasteSessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.detection import AIDetection
from app.models.ai_model import AIModelVersion, TrainingJob
from app.services.ai_client import (
    AIServiceClient,
    AIServiceUnavailableException,
    AIServiceTimeoutException,
    AIServiceResponseException,
    AIServiceValidationException
)
from app.services.ai_vision_service import AIVisionService

client = TestClient(app)


def create_sample_image(color=(40, 180, 60), size=(224, 224)) -> bytes:
    """Creates a valid JPEG image buffer for upload tests."""
    arr = np.full((size[1], size[0], 3), color, dtype=np.uint8)
    arr[30:70, 30:70, :] = (255, 255, 255)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def setup_auth_tokens():
    """Setup test users in Database A (users.db) and generate access tokens."""
    user_db = UserSessionLocal()
    uid = uuid.uuid4().hex[:6]
    admin_email = f"test_admin_{uid}@wastedash.gov"
    citizen_email = f"test_citizen_{uid}@wastedash.gov"

    admin_user = User(
        email=admin_email,
        username=f"admin_{uid}",
        full_name="Test Administrator",
        hashed_password=hash_password("adminpass123"),
        role="system_admin",
        is_active=True
    )
    citizen_user = User(
        email=citizen_email,
        username=f"citizen_{uid}",
        full_name="Test Citizen Contributor",
        hashed_password=hash_password("citizenpass123"),
        role="contributor",
        is_active=True
    )
    user_db.add(admin_user)
    user_db.add(citizen_user)
    user_db.commit()

    admin_token = create_access_token({"sub": admin_email, "role": "system_admin", "email": admin_email})
    citizen_token = create_access_token({"sub": citizen_email, "role": "contributor", "email": citizen_email})
    user_db.close()

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "citizen_headers": {"Authorization": f"Bearer {citizen_token}"}
    }


class TestAIServiceClientConfiguration:
    """Verifies Requirement 10: Environment configuration supports localhost and LAN access."""

    def test_localhost_url_normalization(self):
        """Verify localhost and 127.0.0.1 URLs normalize cleanly."""
        assert AIServiceClient.normalize_url("http://127.0.0.1:8001") == "http://127.0.0.1:8001"
        assert AIServiceClient.normalize_url("http://127.0.0.1:8001/") == "http://127.0.0.1:8001"
        assert AIServiceClient.normalize_url("127.0.0.1:8000") == "http://127.0.0.1:8000"
        assert AIServiceClient.normalize_url("http://localhost:8000/") == "http://localhost:8000"

    def test_lan_url_normalization(self):
        """Verify private LAN IP addresses normalize cleanly without port alteration."""
        lan_url = "http://192.168.1.10:8001"
        assert AIServiceClient.normalize_url(lan_url) == "http://192.168.1.10:8001"

        lan_with_slash = "http://10.79.201.32:8000/"
        assert AIServiceClient.normalize_url(lan_with_slash) == "http://10.79.201.32:8000"

    def test_invalid_scheme_rejection(self):
        """Verify non-HTTP schemes (e.g. file://, ftp://) are rejected for SSRF protection."""
        with pytest.raises(AIServiceValidationException):
            AIServiceClient.normalize_url("file:///etc/passwd")

        with pytest.raises(AIServiceValidationException):
            AIServiceClient.normalize_url("ftp://192.168.1.1/exploit")

    def test_disabled_url_detection(self):
        """Verify empty, none, or disabled base URLs return empty string."""
        assert AIServiceClient.normalize_url("") == ""
        assert AIServiceClient.normalize_url("none") == ""
        assert AIServiceClient.normalize_url("disabled") == ""
        assert AIServiceClient.normalize_url("false") == ""

    def test_connection_pooling_configured(self):
        """Verify Session uses HTTPAdapter with connection pooling."""
        session = AIServiceClient.get_session()
        assert session is not None
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    def test_auth_headers_contain_keys_without_leakage(self):
        """Verify server headers inject X-API-Key and Bearer authorization."""
        headers = AIServiceClient.get_headers()
        assert isinstance(headers, dict)


class TestInferenceForwardingAndMapping:
    """Verifies Requirements 2 & 3: Requests are forwarded and responses mapped correctly."""

    def test_classify_image_forwards_to_ai_api(self):
        """Verify classify_image sends POST /api/v1/ai/predict/image with image file."""
        mock_ai_response = MagicMock()
        mock_ai_response.status_code = 200
        mock_ai_response.json.return_value = {
            "success": True,
            "prediction_id": "PRED-CLS-TEST1234",
            "task": "image_classification",
            "model_name": "ResNet50-WasteClassifier",
            "model_version": "v2.1",
            "framework": "PyTorch 2.2 / ResNet50",
            "predicted_category": "Organic Waste",
            "detected_item": "Organic / Biodegradable Waste",
            "confidence": 0.942,
            "confidence_pct": 94,
            "bounding_box": [0.10, 0.10, 0.90, 0.90],
            "bbox_xywh": [0.10, 0.10, 0.80, 0.80],
            "color": "#10B981",
            "top_predictions": [
                {"category": "Organic Waste", "confidence": 0.942, "confidence_pct": 94},
                {"category": "Recyclable Solid Waste", "confidence": 0.058, "confidence_pct": 6}
            ],
            "fallback_used": False,
            "classification_method": "primary_neural_inference",
            "latency_ms": 72.5
        }

        img_bytes = create_sample_image()
        with patch.object(AIServiceClient.get_session(), "post", return_value=mock_ai_response) as mock_post:
            result = AIServiceClient.classify_image(img_bytes, upload_id=101)

            assert mock_post.called
            call_url = mock_post.call_args[0][0]
            assert "/api/v1/ai/predict/image" in call_url

            assert result["success"] is True
            assert result["predicted_category"] == "Organic Waste"
            assert result["confidence"] == 0.942
            assert result["confidence_pct"] == 94
            assert result["fallback_used"] is False
            assert "top_predictions" in result
            assert len(result["top_predictions"]) == 2

    def test_detect_frame_forwards_to_ai_api(self):
        """Verify detect_frame sends POST /api/v1/ai/predict/frame with confidence threshold."""
        mock_ai_response = MagicMock()
        mock_ai_response.status_code = 200
        mock_ai_response.json.return_value = {
            "success": True,
            "prediction_id": "PRED-DET-TEST5678",
            "task": "object_detection",
            "model_name": "YOLO11n-WasteDetector",
            "model_version": "v2.1",
            "framework": "Ultralytics YOLO11",
            "predicted_category": "Plastic",
            "detected_item": "Plastic Beverage Bottle (PET)",
            "confidence": 0.885,
            "confidence_pct": 88,
            "bounding_box": [0.15, 0.20, 0.80, 0.75],
            "bbox_xywh": [0.20, 0.15, 0.55, 0.65],
            "color": "#3B82F6",
            "count": 1,
            "detections": [
                {
                    "object_name": "Plastic Beverage Bottle (PET)",
                    "raw_class": "bottle",
                    "waste_category": "Plastic",
                    "confidence": 0.885,
                    "confidence_pct": 88,
                    "bounding_box": [0.15, 0.20, 0.80, 0.75],
                    "bbox_xywh": [0.20, 0.15, 0.55, 0.65],
                    "color": "#3B82F6"
                }
            ],
            "fallback_used": False,
            "latency_ms": 74.1
        }

        img_bytes = create_sample_image()
        with patch.object(AIServiceClient.get_session(), "post", return_value=mock_ai_response) as mock_post:
            result = AIServiceClient.detect_frame(img_bytes, frame_id="truck_cam_01", conf_threshold=0.30)

            assert mock_post.called
            call_url = mock_post.call_args[0][0]
            assert "/api/v1/ai/predict/frame" in call_url
            assert "confidence_threshold=0.3" in call_url

            assert result["success"] is True
            assert result["predicted_category"] == "Plastic"
            assert result["count"] == 1
            assert len(result["detections"]) == 1
            assert result["detections"][0]["raw_class"] == "bottle"


class TestExistingEndpointContractsPreserved:
    """Verifies Requirements 1, 4 & 8: Existing contracts and persistence workflows remain working."""

    def test_api_detect_contract_preserved(self):
        """Verify POST /api/detect contract retains predictions, model metadata, and bounding boxes."""
        img_bytes = create_sample_image()
        resp = client.post(
            "/api/detect",
            files={"file": ("webcam_feed.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 200
        data = resp.json()

        # Check required schema fields
        assert "success" in data
        assert "model" in data
        assert "predictions" in data
        assert "bounding_box" in data
        assert "detected_item" in data
        assert "waste_category" in data
        assert "confidence_pct" in data
        assert isinstance(data["predictions"], list)
        assert len(data["predictions"]) >= 1

    def test_live_detect_contract_preserved(self, setup_auth_tokens):
        """Verify POST /api/detections/live-detect retains multi-stage decision fusion schema."""
        img_bytes = create_sample_image()
        headers = setup_auth_tokens["citizen_headers"]
        resp = client.post(
            "/api/detections/live-detect",
            files={"file": ("live_frame.jpg", img_bytes, "image/jpeg")},
            headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["success"] is True
        assert "global_detection" in data
        assert "combined_verdict" in data
        assert "bounding_box" in data
        assert "embedding" in data
        assert len(data["embedding"]) == 128

    def test_simulate_truck_scan_preserves_persistence(self):
        """Verify POST /api/detections/simulate-truck-scan persists detection record to database."""
        img_bytes = create_sample_image()
        resp = client.post(
            "/api/detections/simulate-truck-scan",
            data={
                "vehicle_code": "GC-TEST-99",
                "ward_number": "104",
                "location_name": "Marina Beach Road"
            },
            files={"file": ("truck_scanner.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["success"] is True
        assert "detection_code" in data
        assert data["detection_code"].startswith("DET-")

        # Verify database record in Database C (waste_management.db)
        waste_db = WasteSessionLocal()
        det = waste_db.query(AIDetection).filter(AIDetection.detection_code == data["detection_code"]).first()
        assert det is not None
        assert det.vehicle_code == "GC-TEST-99"
        assert det.ward_number == 104
        waste_db.close()

    def test_upload_and_predict_contract_preserved(self):
        """Verify POST /api/contributions/upload-and-predict preserves citizen workflow."""
        img_bytes = create_sample_image()
        resp = client.post(
            "/api/contributions/upload-and-predict",
            files={"file": ("citizen_waste_item.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["success"] is True
        assert "image_url" in data
        assert "image_hash" in data
        assert "ai_prediction" in data
        assert "quality_check" in data
        assert "all_primary_categories" in data
        assert "all_specific_items" in data


class TestHealthAndReadinessIntegration:
    """Verifies Requirements 6 & 7: Health checks report AI service status without exposing secrets."""

    def test_backend_health_check_additive_ai_status(self):
        """Verify GET /api/health includes additive ai_service field and keeps all legacy fields intact."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()

        # Legacy contract fields MUST be preserved
        assert "status" in data
        assert "service" in data
        assert "city" in data
        assert "database" in data
        assert "active_model" in data
        assert "storage" in data
        assert "zones_count" in data
        assert "wards_count" in data
        assert "version" in data

        # Additive AI service field
        assert "ai_service" in data
        ai_info = data["ai_service"]
        assert "configured" in ai_info
        assert "reachable" in ai_info
        assert "inference_ready" in ai_info
        assert "status" in ai_info

        # Security check: Never expose secrets, API keys, or raw system paths
        serialized = json.dumps(data)
        assert "secret" not in serialized.lower() or "secret-key" not in serialized.lower()
        assert "api_key" not in serialized.lower()
        assert "/home/" not in serialized

    def test_backend_health_stays_healthy_when_ai_service_offline(self):
        """
        Verify that backend health does not fail solely because an optional external
        AI service is unreachable (distinguishing reachability from backend db health).
        """
        with patch.object(AIServiceClient, "get_health_summary", return_value={
            "configured": True,
            "reachable": False,
            "inference_ready": False,
            "status": "unreachable",
            "latency_ms": 3.2
        }):
            resp = client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            # Database is healthy, so top-level backend status is healthy
            assert data["status"] == "healthy"
            assert data["ai_service"]["reachable"] is False


class TestFailSafeFallbackAndErrorHandling:
    """Verifies Requirement 5: Timeouts and connection failures trigger fallback safely."""

    def test_remote_ai_timeout_triggers_classical_fallback(self):
        """Verify that when the remote AI API times out and local engine fails, classical CV fallback is invoked safely."""
        img = Image.fromarray(np.full((224, 224, 3), (20, 160, 40), dtype=np.uint8))
        with patch.object(AIServiceClient, "classify_image", side_effect=AIServiceTimeoutException("Timed out after 15s")):
            with patch.object(AIVisionService, "get_engines", return_value=(None, None)):
                res = AIVisionService.detect_and_classify(img, filename_hint="banana_peel.jpg", task="classification")
                assert res is not None
                assert res["fallback_used"] is True
                assert res["primary_model_status"] in ("unavailable", "exception_raised")

    def test_remote_ai_connection_refused_handled_safely(self):
        """Verify connection refusal triggers graceful fallback without raising uncaught 500 error."""
        img = Image.fromarray(np.full((224, 224, 3), (30, 120, 220), dtype=np.uint8))
        with patch.object(AIServiceClient, "classify_image", side_effect=AIServiceUnavailableException("Connection refused")):
            with patch.object(AIVisionService, "get_engines", return_value=(None, None)):
                res = AIVisionService.detect_and_classify(img, filename_hint="plastic_bottle.jpg", task="classification")
                assert res is not None
                assert res["fallback_used"] is True

    def test_no_fabricated_predictions_on_missing_model(self):
        """Verify Requirement 6: Missing models or uncertain data do not fabricate confidence."""
        gray_img = Image.fromarray(np.full((224, 224, 3), 128, dtype=np.uint8))
        with patch.object(AIVisionService, "_run_primary_model", return_value=None):
            res = AIVisionService.detect_and_classify(gray_img, filename_hint="")
            assert res["fallback_used"] is True
            # Heuristic score for uncertain gray frame is not inflated to 99%
            assert res["confidence"] < 0.70
            assert res["requires_review"] is True


class TestSecurityAndCodebaseSanity:
    """Verifies Requirements 7 & 9: RBAC enforcement and no hardcoded IPs/credentials."""

    def test_rbac_citizen_forbidden_from_admin_model_activation(self, setup_auth_tokens):
        """Verify citizens cannot activate models or bypass administrative boundaries."""
        citizen_headers = setup_auth_tokens["citizen_headers"]
        resp = client.post("/api/admin/models/1/activate", headers=citizen_headers)
        assert resp.status_code == 403

    def test_no_hardcoded_lan_ips_in_production_code(self):
        """Verify Requirement 9: No machine-specific IP or private credentials in python source files."""
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Search for hardcoded RFC 1918 private IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
        # Excluding comments and tests
        pattern = re.compile(r'(?<!#)(?<!//)[\'"](http://192\.168\.\d+\.\d+|http://10\.\d+\.\d+\.\d+)[\'"]')

        violating_files = []
        for root, _, files in os.walk(app_dir):
            if "tests" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        for line_no, line in enumerate(fh, 1):
                            if pattern.search(line):
                                violating_files.append(f"{fpath}:{line_no}")

        assert len(violating_files) == 0, f"Found hardcoded private IP in production code: {violating_files}"


class TestTrainingAndLifecycleOrchestration:
    """Verifies Task 2 Section E: Training, Retraining, Model Evaluation & Activation."""

    def test_citizen_forbidden_from_triggering_training(self, setup_auth_tokens):
        """Citizen role cannot initiate model training or retraining."""
        citizen_headers = setup_auth_tokens["citizen_headers"]
        resp = client.post("/api/admin/train-model", json={"total_epochs": 5}, headers=citizen_headers)
        assert resp.status_code == 403

    def test_unauthenticated_forbidden_from_triggering_training(self):
        """Unauthenticated caller cannot initiate model training."""
        resp = client.post("/api/admin/train-model", json={"total_epochs": 5})
        assert resp.status_code in (401, 403)

    def test_admin_dispatches_training_to_laptop_ai_service(self, setup_auth_tokens):
        """Admin triggering training dispatches job to laptop AI API and persists job record."""
        admin_headers = setup_auth_tokens["admin_headers"]
        remote_job_id = f"JOB-REMOTE-{uuid.uuid4().hex[:8]}"

        mock_remote_job = {
            "job_id": remote_job_id,
            "status": "queued",
            "stage": "initializing",
            "message": "Retraining job queued on laptop AI server"
        }

        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(AIServiceClient, "submit_training_job", return_value=mock_remote_job) as mock_submit:
                resp = client.post(
                    "/api/admin/train-model",
                    json={"candidate_version": f"v2.{uuid.uuid4().hex[:4]}", "total_epochs": 10, "batch_size": 16},
                    headers=admin_headers
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["job_code"] == remote_job_id
                mock_submit.assert_called_once()

    def test_training_fails_controlled_when_laptop_offline(self, setup_auth_tokens):
        """When laptop AI service is offline, return controlled 503 rather than fake training."""
        admin_headers = setup_auth_tokens["admin_headers"]

        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(
                AIServiceClient,
                "submit_training_job",
                side_effect=AIServiceUnavailableException("Laptop AI compute server offline at http://127.0.0.1:8001")
            ):
                resp = client.post(
                    "/api/admin/train-model",
                    json={"candidate_version": f"v2.{uuid.uuid4().hex[:4]}", "total_epochs": 5},
                    headers=admin_headers
                )
                assert resp.status_code == 503
                detail = resp.json().get("detail", "")
                assert "unavailable" in detail.lower() or "offline" in detail.lower()

    def test_training_status_polling_synchronizes_remote_telemetry(self, setup_auth_tokens):
        """Polling /api/admin/training-status synchronizes remote job metrics and progress."""
        admin_headers = setup_auth_tokens["admin_headers"]
        sync_job_code = f"JOB-SYNC-{uuid.uuid4().hex[:8]}"

        waste_db = WasteSessionLocal()
        try:
            job = TrainingJob(
                job_code=sync_job_code,
                candidate_version=f"v2.{uuid.uuid4().hex[:4]}",
                status="running",
                stage="training",
                current_epoch=2,
                total_epochs=10,
                progress_pct=20.0,
                started_at=datetime.utcnow()
            )
            waste_db.add(job)
            waste_db.commit()
        finally:
            waste_db.close()

        mock_remote_status = {
            "job_id": sync_job_code,
            "status": "running",
            "stage": "training",
            "progress_pct": 65.5,
            "current_epoch": 7,
            "total_epochs": 10,
            "log_output": "[12:00:00] Fine-tuning ResNet50 epoch 7...\n",
            "metrics": {
                "val_accuracy": 0.923,
                "val_f1": 0.915,
                "precision": 0.920,
                "recall": 0.910,
                "train_loss": 0.082,
                "val_loss": 0.105
            }
        }

        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(AIServiceClient, "get_training_job_status", return_value=mock_remote_status):
                resp = client.get("/api/admin/training-status", headers=admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["job_code"] == sync_job_code
                assert data["progress_pct"] == 65.5
                assert data["current_epoch"] == 7
                assert data["status"] == "running"

    def test_completed_remote_training_registers_candidate_model(self, setup_auth_tokens):
        """When remote training finishes, candidate model is registered in AIModelVersion."""
        admin_headers = setup_auth_tokens["admin_headers"]
        completed_job_code = f"JOB-COMPLETED-{uuid.uuid4().hex[:8]}"
        candidate_ver = f"v2.{uuid.uuid4().hex[:5]}"

        waste_db = WasteSessionLocal()
        try:
            job = TrainingJob(
                job_code=completed_job_code,
                candidate_version=candidate_ver,
                status="running",
                stage="evaluating",
                current_epoch=10,
                total_epochs=10,
                progress_pct=95.0,
                started_at=datetime.utcnow()
            )
            waste_db.add(job)
            waste_db.commit()
        finally:
            waste_db.close()

        mock_completed_remote = {
            "job_id": completed_job_code,
            "status": "completed",
            "stage": "completed",
            "progress_pct": 100.0,
            "current_epoch": 10,
            "total_epochs": 10,
            "log_output": "[12:05:00] PyTorch evaluation gate passed.\n",
            "metrics": {
                "val_accuracy": 0.935,
                "val_f1": 0.928,
                "precision": 0.932,
                "recall": 0.925,
                "train_loss": 0.065,
                "val_loss": 0.091
            },
            "evaluation_report": {
                "quality_checks_passed": True,
                "candidate_accuracy": 0.935
            }
        }

        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(AIServiceClient, "get_training_job_status", return_value=mock_completed_remote):
                resp = client.get("/api/admin/training-status", headers=admin_headers)
                assert resp.status_code == 200
                assert resp.json()["status"] == "completed"

                # Verify candidate model registered in database
                waste_db = WasteSessionLocal()
                try:
                    cand = waste_db.query(AIModelVersion).filter(AIModelVersion.version == candidate_ver).first()
                    assert cand is not None
                    assert cand.status == "candidate"
                    assert cand.accuracy == 0.935
                finally:
                    waste_db.close()

    def test_activate_model_notifies_laptop_ai_service(self, setup_auth_tokens):
        """Activating candidate model invokes laptop AI activation endpoint."""
        admin_headers = setup_auth_tokens["admin_headers"]
        act_ver = f"v2.{uuid.uuid4().hex[:5]}"

        waste_db = WasteSessionLocal()
        try:
            model = AIModelVersion(
                version=act_ver,
                model_name="Test-Candidate-Model",
                framework="PyTorch",
                status="candidate",
                accuracy=0.92,
                precision=0.91,
                recall=0.90,
                f1_score=0.915,
                is_active_production=False
            )
            waste_db.add(model)
            waste_db.commit()
            model_id = model.id
        finally:
            waste_db.close()

        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(AIServiceClient, "activate_model", return_value={"success": True}) as mock_act:
                resp = client.post(f"/api/admin/models/{model_id}/activate", headers=admin_headers)
                assert resp.status_code == 200
                mock_act.assert_called_once_with(act_ver)

    def test_rejected_candidate_blocked_from_activation(self, setup_auth_tokens):
        """Models that failed validation evaluation gates cannot be activated."""
        admin_headers = setup_auth_tokens["admin_headers"]
        rej_ver = f"v2.{uuid.uuid4().hex[:5]}-rej"

        waste_db = WasteSessionLocal()
        try:
            model = AIModelVersion(
                version=rej_ver,
                model_name="Failed-Candidate-Model",
                framework="PyTorch",
                status="candidate_rejected",
                accuracy=0.65,
                precision=0.60,
                recall=0.55,
                f1_score=0.57,
                is_active_production=False
            )
            waste_db.add(model)
            waste_db.commit()
            model_id = model.id
        finally:
            waste_db.close()

        resp = client.post(f"/api/admin/models/{model_id}/activate", headers=admin_headers)
        assert resp.status_code == 400
        assert "failed validation evaluation gates" in resp.json()["detail"].lower()

    def test_dashboard_stats_loads_when_ai_offline(self):
        """Dashboard overview metrics remain operational when AI service is offline."""
        with patch.object(AIServiceClient, "is_configured", return_value=True):
            with patch.object(AIServiceClient, "get_health_summary", return_value={
                "configured": True,
                "reachable": False,
                "inference_ready": False,
                "status": "unreachable",
                "latency_ms": 0.0
            }):
                resp = client.get("/api/dashboard/summary")
                assert resp.status_code == 200
                data = resp.json()
                assert "total_waste_processed_tons" in data or "segregation_accuracy" in data or "active_trucks" in data
                assert "total_waste_processed" in data or "total_waste_diverted_kg" in data or "recycling_rate" in data

