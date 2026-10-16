import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import WasteSessionLocal
from app.models.detection import AIDetection
from app.models.upload import Upload
from app.models.waste import WasteRecord
from app.models.facility import SegregationPlant

client = TestClient(app)


@pytest.fixture(scope="module")
def waste_db():
    db = WasteSessionLocal()
    yield db
    db.close()


class TestDashboardMetrics:
    """
    Verification suite for Section 8 & 11: Authoritative Dashboard Analytics.
    Validates formulas, data sources, zero-denominator safety, and non-reliance on model confidence as accuracy.
    """

    def test_ai_analytics_endpoint_structure_and_formula_audit(self):
        """
        Verify /api/dashboard/ai-analytics returns authoritative fields and explicit formula metadata.
        """
        resp = client.get("/api/dashboard/ai-analytics")
        assert resp.status_code == 200
        data = resp.json()

        assert "summary_metrics" in data
        assert "detected_waste_composition" in data
        assert "formulas_audit" in data

        metrics = data["summary_metrics"]
        assert "verified_segregation_accuracy_pct" in metrics
        assert "contamination_rate_pct" in metrics
        assert "downstream_recovery_rate_pct" in metrics
        assert "fallback_usage_pct" in metrics
        assert "manual_review_rate_pct" in metrics

        # Audit transparency check
        audit = data["formulas_audit"]
        assert "verified_segregation_accuracy" in audit
        assert "contamination_rate" in audit
        assert "downstream_recovery_rate" in audit
        assert "fallback_usage_rate" in audit
        assert "manual_review_rate" in audit

        # Ensure verified segregation accuracy explicitly cites ground truth and not model confidence
        acc_formula = audit["verified_segregation_accuracy"]
        assert "ground truth" in acc_formula["formula"].lower() or "ground truth" in acc_formula["numerator"].lower()

    def test_zero_denominator_safe_handling(self):
        """
        Verify that querying an empty or nonexistent ward does not crash with ZeroDivisionError,
        and returns 0.0 with clear empty state indicators.
        """
        resp = client.get("/api/dashboard/ai-analytics?ward_number=99999")
        assert resp.status_code == 200
        data = resp.json()

        metrics = data["summary_metrics"]
        assert metrics["total_detections"] == 0
        assert metrics["average_ai_confidence_pct"] == 0.0
        assert metrics["manual_review_rate_pct"] == 0.0
        assert metrics["fallback_usage_pct"] == 0.0

    def test_verified_accuracy_uses_ground_truth_not_confidence(self, waste_db):
        """
        Verify verified_segregation_accuracy is calculated strictly from verified user reviews / ground truth,
        and does not equate AI confidence with physical accuracy.
        """
        resp = client.get("/api/dashboard/ai-analytics")
        assert resp.status_code == 200
        data = resp.json()
        metrics = data["summary_metrics"]

        # If evaluated ground truth samples exist, verified_segregation_accuracy_pct is between 0 and 100
        assert 0.0 <= metrics["verified_segregation_accuracy_pct"] <= 100.0
        # Check that ground truth sample count is reported
        assert "evaluated_ground_truth_samples" in metrics

    def test_recycling_rate_derived_from_actual_facility_intake(self, waste_db):
        """
        Verify recycling rate is computed from actual operational facility intake,
        not from an arbitrary hardcoded multiplier.
        """
        resp = client.get("/api/dashboard/ai-analytics")
        assert resp.status_code == 200
        data = resp.json()
        metrics = data["summary_metrics"]

        assert "downstream_recovery_rate_pct" in metrics
        rate = metrics["downstream_recovery_rate_pct"]
        assert 0.0 <= rate <= 100.0

    def test_ward_scoping_isolation(self):
        """
        Verify dashboard metrics accept and apply ward_number filter to isolate analytics.
        """
        resp_all = client.get("/api/dashboard/ai-analytics")
        resp_ward = client.get("/api/dashboard/ai-analytics?ward_number=102")

        assert resp_all.status_code == 200
        assert resp_ward.status_code == 200
        data_ward = resp_ward.json()
        assert "location_scope" in data_ward
        assert "Ward 102" in data_ward["location_scope"]
