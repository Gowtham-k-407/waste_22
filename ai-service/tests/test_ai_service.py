import io
import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_test_image(color=(40, 160, 50), size=(224, 224)) -> bytes:
    arr = np.full((size[1], size[0], 3), color, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestStandaloneAIService:
    """Test suite for the independent standalone AI microservice."""

    def test_health_endpoints(self):
        """Verify health endpoints return model readiness for ResNet50 and YOLO11n."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "ready")
        assert "resnet50_ready" in data
        assert "yolo11n_ready" in data
        assert data["resnet50_ready"] is True
        assert data["yolo11n_ready"] is True

        resp_v1 = client.get("/api/v1/ai/health")
        assert resp_v1.status_code == 200

    def test_models_registry_and_active(self):
        """Verify model registry and active models."""
        resp = client.get("/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data

        resp_act = client.get("/models/active")
        assert resp_act.status_code == 200
        act_data = resp_act.json()
        assert "classification" in act_data
        assert "detection" in act_data

    def test_predict_image_classification(self):
        """Verify ResNet50 image classification endpoint."""
        img_bytes = make_test_image()
        resp = client.post(
            "/api/v1/ai/predict/image",
            files={"file": ("test_leaf.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task"] == "image_classification"
        assert "predicted_category" in data
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0

    def test_predict_frame_detection(self):
        """Verify YOLO11n frame detection endpoint."""
        img_bytes = make_test_image(color=(128, 128, 128), size=(320, 320))
        resp = client.post(
            "/api/v1/ai/predict/frame",
            files={"file": ("test_frame.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task"] == "object_detection"
        assert "detections" in data
        assert "count" in data

    def test_universal_predict_router(self):
        """Verify universal /predict endpoint routes tasks appropriately."""
        img_bytes = make_test_image()

        # Classification task
        resp_cls = client.post(
            "/predict?task=classification",
            files={"file": ("item.jpg", img_bytes, "image/jpeg")}
        )
        assert resp_cls.status_code == 200
        assert resp_cls.json()["task"] == "image_classification"

        # Detection task
        resp_det = client.post(
            "/predict?task=detection",
            files={"file": ("item.jpg", img_bytes, "image/jpeg")}
        )
        assert resp_det.status_code == 200
        assert resp_det.json()["task"] == "object_detection"

    def test_fallback_status(self):
        """Verify fallback engine status and calibration."""
        resp = client.get("/fallback/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "fallback_algorithm" in data
        assert data["status"] in ("ready", "operational")
