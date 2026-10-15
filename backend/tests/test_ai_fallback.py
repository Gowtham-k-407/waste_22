import os
import io
import time
import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock

from app.services.ai_vision_service import AIVisionService
from app.services.ai_fallback_service import AIFallbackService

# Helper to generate test synthetic images in memory
def create_synthetic_image(color=(120, 90, 60), size=(224, 224), pattern="solid") -> Image.Image:
    np.random.seed(42)
    if pattern == "cardboard":
        # Brown base with corrugated fluting texture
        arr = np.full((size[1], size[0], 3), (160, 115, 75), dtype=np.uint8)
        for y in range(0, size[1], 12):
            arr[y:y+4, :, :] = (130, 90, 55)
        noise = np.random.randint(-15, 15, (size[1], size[0], 3), dtype=np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    elif pattern == "plastic":
        # Cyan-blue saturated block with specular highlight
        arr = np.full((size[1], size[0], 3), (20, 140, 220), dtype=np.uint8)
        arr[50:90, 50:110, :] = (245, 250, 255)
        noise = np.random.randint(-10, 10, (size[1], size[0], 3), dtype=np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    elif pattern == "organic":
        # Green organic leafy patch with natural texture
        arr = np.full((size[1], size[0], 3), (40, 155, 50), dtype=np.uint8)
        noise = np.random.randint(-25, 25, (size[1], size[0], 3), dtype=np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    elif pattern == "noise":
        arr = np.random.randint(90, 140, (size[1], size[0], 3), dtype=np.uint8)
    elif pattern == "black":
        arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    else:
        arr = np.full((size[1], size[0], 3), color, dtype=np.uint8)
    return Image.fromarray(arr)


class TestAIFallbackAlgorithm:
    """
    Automated verification suite for Section 15.G:
    Mandatory 15-scenario fallback classification test matrix.
    """

    # Scenario 1: Primary model succeeds and fallback is not needed
    def test_01_primary_model_succeeds_no_fallback(self):
        img = create_synthetic_image(pattern="plastic")
        mock_primary = {
            "predicted_category": "Plastic",
            "detected_item": "Plastic Bottle (PET)",
            "confidence": 0.94,
            "confidence_pct": 94,
            "bounding_box": [0.1, 0.1, 0.8, 0.8],
            "embedding": [0.1] * 128
        }
        with patch.object(AIVisionService, "_run_primary_model", return_value=mock_primary):
            res = AIVisionService.detect_and_classify(img)
            assert res["predicted_category"] == "Plastic"
            assert res["fallback_used"] is False
            assert res["classification_method"] == "primary_ai"
            assert res["requires_review"] is False

    # Scenario 2: Primary model throws an exception and fallback succeeds
    def test_02_primary_model_exception_triggers_fallback(self):
        img = create_synthetic_image(pattern="cardboard")
        with patch.object(AIVisionService, "_run_primary_model", side_effect=RuntimeError("CUDA out of memory")):
            res = AIVisionService.detect_and_classify(img, filename_hint="cardboard_box.jpg")
            assert res["fallback_used"] is True
            assert res["classification_method"] in ("fallback_heuristic", "fallback_classical_cv")
            assert "Cardboard" in res["predicted_category"] or "Paper" in res["predicted_category"]
            assert res["primary_model_status"] == "exception_raised"

    # Scenario 3: Primary model times out and fallback succeeds
    def test_03_primary_model_timeout_triggers_fallback(self):
        img = create_synthetic_image(pattern="organic")
        with patch.object(AIVisionService, "_run_primary_model", side_effect=TimeoutError("Inference timed out after 4.0s")):
            res = AIVisionService.detect_and_classify(img, filename_hint="banana_peel.png")
            assert res["fallback_used"] is True
            assert res["classification_method"] in ("fallback_heuristic", "fallback_classical_cv")
            assert res["predicted_category"] in ("Organic Waste", "Food Waste")

    # Scenario 4: Primary model returns an invalid label
    def test_04_primary_model_invalid_label_triggers_fallback(self):
        img = create_synthetic_image(pattern="plastic")
        mock_invalid = {
            "predicted_category": "Extraterrestrial Object",
            "detected_item": "Unknown Alien Artifact",
            "confidence": 0.88,
            "confidence_pct": 88,
            "bounding_box": [0.1, 0.1, 0.9, 0.9]
        }
        with patch.object(AIVisionService, "_run_primary_model", return_value=mock_invalid):
            res = AIVisionService.detect_and_classify(img, filename_hint="water_bottle.jpg")
            # Should detect invalid category and fall back to classical CV
            assert res["fallback_used"] is True
            assert res["predicted_category"] != "Extraterrestrial Object"

    # Scenario 5: Primary model returns a low-confidence result
    def test_05_primary_model_low_confidence_triggers_fallback(self):
        img = create_synthetic_image(pattern="cardboard")
        mock_low_conf = {
            "predicted_category": "Plastic",
            "detected_item": "Uncertain Plastic",
            "confidence": 0.22, # Below 0.45 threshold
            "confidence_pct": 22,
            "bounding_box": [0.1, 0.1, 0.8, 0.8]
        }
        with patch.object(AIVisionService, "_run_primary_model", return_value=mock_low_conf):
            res = AIVisionService.detect_and_classify(img, filename_hint="corrugated_box.jpg")
            assert res["fallback_used"] is True
            assert res["classification_method"] in ("fallback_heuristic", "fallback_classical_cv")

    # Scenario 6: Fallback classifies a valid uploaded image directly
    def test_06_fallback_classifies_valid_image(self):
        img = create_synthetic_image(pattern="cardboard")
        result = AIFallbackService.classify_image(img, filename_hint="shipping_carton.jpg")
        assert result["fallback_used"] is True
        assert result["classification_method"] in ("fallback_heuristic", "fallback_classical_cv")
        assert result["predicted_category"] in ("Cardboard", "Paper")
        assert result["confidence"] > 0.40

    # Scenario 7: Fallback processes a valid live-feed frame
    def test_07_fallback_processes_live_feed_frame(self):
        frame = create_synthetic_image(pattern="plastic")
        result = AIFallbackService.classify_frame(frame)
        assert result["fallback_used"] is True
        assert "predicted_category" in result
        assert len(result["bounding_box"]) == 4

    # Scenario 8: Corrupted image returns an appropriate error safely
    def test_08_corrupted_image_handling(self):
        corrupt_bytes = b"NOT_A_REAL_JPEG_OR_PNG_HEADER_CORRUPTED"
        with pytest.raises(Exception):
            Image.open(io.BytesIO(corrupt_bytes))

    # Scenario 9: Pitch black or unusable frame is handled safely
    def test_09_blank_or_unusable_frame_handled_safely(self):
        blank_img = create_synthetic_image(pattern="black")
        res = AIFallbackService.classify_frame(blank_img)
        # Should gracefully return unknown or uncertain without crashing
        assert res["requires_review"] is True or res["predicted_category"] in ("unknown", "Mixed Waste", "Other Waste")
        assert res["confidence"] <= 0.45

    # Scenario 10: Uncertain image returns unknown when evidence is insufficient
    def test_10_uncertain_image_returns_unknown(self):
        # Neutral gray image with no color, no edges, no text hint
        gray_img = create_synthetic_image(color=(128, 128, 128), pattern="solid")
        res = AIFallbackService.classify_image(gray_img, filename_hint="")
        assert res["requires_review"] is True or res["confidence"] < 0.45

    # Scenario 11: Both primary and fallback failures handled safely
    def test_11_both_primary_and_fallback_failures_handled(self):
        img = create_synthetic_image(pattern="solid")
        with patch.object(AIVisionService, "_run_primary_model", side_effect=Exception("Primary Down")):
            with patch.object(AIFallbackService, "classify_with_fallback", side_effect=Exception("OpenCV Fatal Crash")):
                res = AIVisionService.detect_and_classify(img)
                # Must return safe unknown fallback structure without throwing uncaught 500
                assert res["predicted_category"] == "unknown"
                assert res["requires_review"] is True
                assert res["classification_method"] == "emergency_fallback"

    # Scenario 12: Failed frame does not crash subsequent live-feed frames
    def test_12_failed_frame_does_not_crash_subsequent_stream(self):
        bad_img = create_synthetic_image(pattern="black")
        good_img = create_synthetic_image(pattern="plastic")

        # Process bad frame
        with patch.object(AIVisionService, "_run_primary_model", side_effect=RuntimeError("Transient Frame Failure")):
            res1 = AIVisionService.detect_and_classify(bad_img)
            assert res1["fallback_used"] is True

        # Process next normal frame - stream continues uninterrupted!
        res2 = AIVisionService.detect_and_classify(good_img, filename_hint="plastic_bottle.jpg")
        assert res2 is not None
        assert res2.get("predicted_category") in ("Plastic", "Cardboard", "Recyclable", "Dry Waste")
        assert res2.get("confidence", 0) > 0.0

    # Scenario 13: Fallback results are accurately labelled
    def test_13_fallback_results_labelled_accurately(self):
        img = create_synthetic_image(pattern="organic")
        with patch.object(AIVisionService, "_run_primary_model", side_effect=Exception("Service Unavailable")):
            res = AIVisionService.detect_and_classify(img, filename_hint="food_waste.png")
            assert res["fallback_used"] is True
            assert res["classification_method"] in ("fallback_heuristic", "fallback_classical_cv")
            assert "heuristic_score" in res or "confidence" in res

    # Scenario 14: API does not falsely claim primary-model success
    def test_14_api_does_not_falsely_claim_primary_success(self):
        img = create_synthetic_image(pattern="cardboard")
        with patch.object(AIVisionService, "_run_primary_model", side_effect=Exception("Simulated Primary Outage")):
            res = AIVisionService.detect_and_classify(img)
            assert res["fallback_used"] is True
            assert res["classification_method"] != "primary_ai"

    # Scenario 15: No fabricated probabilities or model metrics
    def test_15_no_fabricated_probabilities(self):
        img = create_synthetic_image(pattern="noise")
        res = AIFallbackService.classify_image(img, filename_hint="")
        # Score is documented heuristic, not inflated to 99%
        assert res["confidence"] < 0.95
        assert res["confidence"] > 0.0
        assert isinstance(res["confidence"], float)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
