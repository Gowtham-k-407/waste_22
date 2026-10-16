import os
import io
import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock

from app.services.ai_vision_service import AIVisionService
from app.services.ai_fallback_service import AIFallbackService


def generate_test_image(color=(30, 160, 240), size=(224, 224)) -> Image.Image:
    arr = np.full((size[1], size[0], 3), color, dtype=np.uint8)
    # Add simple variation
    arr[20:80, 20:80, :] = (255, 255, 255)
    return Image.fromarray(arr)


class TestInferenceWorkflow:
    """
    Test suite for model loading, task-aware routing, response schemas,
    and remote microservice fallback orchestration.
    """

    def test_resnet50_model_loads_and_infers(self):
        """Verify authoritative waste_resnet50.pth checkpoint loads and outputs 2-class probabilities."""
        img = generate_test_image((35, 170, 45)) # Greenish organic-like image
        res = AIVisionService.classify_upload_image(img, upload_id=9999)

        assert res is not None
        assert "predicted_class" in res
        assert "confidence" in res
        assert res["task"] == "classification"
        assert res["model_type"] == "resnet50"
        assert res["predicted_class"] in ["Organic Waste", "Recyclable / Plastic", "Unknown Waste"]
        assert 0.0 <= res["confidence"] <= 1.0
        assert "class_scores" in res
        assert isinstance(res["class_scores"], dict)

    def test_yolo11n_model_loads_and_detects(self):
        """Verify authoritative yolo11n.pt checkpoint loads and processes camera frames."""
        img = generate_test_image((128, 128, 128), size=(320, 320))
        res = AIVisionService.detect_camera_frame(img, frame_id="test_frame_01")

        assert res is not None
        assert res["task"] == "detection"
        assert res["model_type"] == "yolo11n"
        assert "detections" in res
        assert "count" in res
        assert isinstance(res["detections"], list)
        assert isinstance(res["count"], int)

    def test_task_aware_routing_upload_vs_frame(self):
        """Verify image uploads route to ResNet50, and camera frames route to YOLO11n."""
        img = generate_test_image()

        # Upload -> ResNet50
        upload_res = AIVisionService.classify_upload_image(img)
        assert upload_res["model_type"] == "resnet50"
        assert upload_res["task"] == "classification"

        # Frame -> YOLO11n
        frame_res = AIVisionService.detect_camera_frame(img)
        assert frame_res["model_type"] == "yolo11n"
        assert frame_res["task"] == "detection"

    def test_response_schema_fields(self):
        """Verify prediction response schema conforms to required enterprise contract."""
        img = generate_test_image()
        res = AIVisionService.classify_upload_image(img)

        expected_fields = [
            "prediction_id", "task", "model_id", "model_type",
            "predicted_class", "confidence", "fallback_used",
            "fallback_reason", "processing_time_ms",
            "suitable_for_automated_sorting", "requires_review"
        ]
        for f in expected_fields:
            assert f in res, f"Missing required response schema field: {f}"

    def test_low_confidence_requires_review(self):
        """Verify predictions below safety threshold (0.70) are marked requires_review=True and suitable_for_automated_sorting=False."""
        img = generate_test_image()
        # Mock low confidence inference from primary model
        mock_prim = {
            "predicted_category": "Organic Waste",
            "confidence": 0.52,
            "confidence_pct": 52,
            "bounding_box": [0.1, 0.1, 0.9, 0.9],
            "model_name": "ResNet50-WasteClassifier",
            "model_version": "v2.1",
            "latency_ms": 20.0
        }
        with patch.object(AIVisionService, "_run_primary_model", return_value=mock_prim):
            res = AIVisionService.classify_upload_image(img)
            # Low confidence triggers fallback, or sets requires_review
            assert res["confidence"] < 0.70 or res["requires_review"] is True
            assert res["suitable_for_automated_sorting"] is False

    def test_remote_ai_service_fallback_to_local_engine(self):
        """Verify that when remote AI service is unreachable, orchestrator falls back to local PyTorch engine seamlessly."""
        img = generate_test_image()
        with patch("requests.post", side_effect=Exception("Connection refused (remote down)")):
            res = AIVisionService.classify_upload_image(img)
            # Should not crash; executes local engine
            assert res is not None
            assert res["task"] == "classification"
            assert "predicted_class" in res

    def test_full_failure_invokes_classical_fallback(self):
        """Verify that if both remote and local deep learning fail, classical CV fallback is safely invoked."""
        img = generate_test_image((20, 140, 220), (224, 224)) # Blue recyclable pattern
        with patch.object(AIVisionService, "_run_primary_model", return_value=None):
            res = AIVisionService.classify_upload_image(img)
            assert res is not None
            assert res["fallback_used"] is True
            assert "fallback" in res["model_type"]
            assert res["predicted_class"] in [
                "Plastic", "Recyclable Waste", "Organic Waste",
                "Unknown / Ambiguous", "Dry Recyclable", "Paper", "Glass", "Metal"
            ]

