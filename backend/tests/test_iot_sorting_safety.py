import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import WasteSessionLocal
from app.models.iot import IoTSortingRecord
from app.services.iot_sorting_service import IoTSortingSafetyService

client = TestClient(app)


@pytest.fixture(scope="module")
def waste_db():
    db = WasteSessionLocal()
    yield db
    db.close()


class TestIoTSortingSafety:
    """
    Verification suite for Section 9: IoT Sorting Safety Layer.
    Tests destination mapping, confidence threshold (>= 0.70), fallback exclusion,
    emergency stop lockouts, break-beam verification, and idempotency.
    """

    def setup_method(self):
        # Ensure emergency stop is reset before each test
        IoTSortingSafetyService.set_emergency_stop(False)
        IoTSortingSafetyService.set_actuator_health(True)

    def teardown_method(self):
        IoTSortingSafetyService.set_emergency_stop(False)
        IoTSortingSafetyService.set_actuator_health(True)

    def test_category_to_bin_mapping(self):
        """Verify category routing maps to bins 1, 2, 3, or 4 correctly."""
        # Organic -> Bin 1
        assert IoTSortingSafetyService.resolve_target_bin("Organic Waste") == 1
        assert IoTSortingSafetyService.resolve_target_bin("Food Waste") == 1
        assert IoTSortingSafetyService.resolve_target_bin("banana") == 1

        # Recyclable -> Bin 2
        assert IoTSortingSafetyService.resolve_target_bin("Plastic") == 2
        assert IoTSortingSafetyService.resolve_target_bin("bottle") == 2
        assert IoTSortingSafetyService.resolve_target_bin("Cardboard") == 2

        # E-Waste -> Bin 3
        assert IoTSortingSafetyService.resolve_target_bin("E-Waste") == 3
        assert IoTSortingSafetyService.resolve_target_bin("cell phone") == 3
        assert IoTSortingSafetyService.resolve_target_bin("laptop") == 3

        # Unknown / Ambiguous -> Bin 4 (Reject)
        assert IoTSortingSafetyService.resolve_target_bin("Unknown Item") == 4
        assert IoTSortingSafetyService.resolve_target_bin("Unidentifiable Residue") == 4

    def test_high_confidence_primary_detection_executes(self):
        """Verify high confidence (>= 0.70) primary prediction triggers execution to target bin."""
        uid = f"cmd_safe_{uuid.uuid4().hex[:6]}"
        payload = {
            "item_label": "High Quality PET Bottle",
            "detected_category": "Plastic Waste",
            "confidence": 0.94,
            "is_fallback": False,
            "event_id": uid
        }
        resp = client.post("/api/iot/sorting/command", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["event_id"] == uid
        assert data["status"] == "executed"
        assert data["bin_index"] == 2
        assert data["target_bin"] == "bin_2_recyclables"
        assert data["sensor_verification_status"] == "verified"
        assert data["actuator_latency_ms"] > 0.0

    def test_low_confidence_diverted_to_reject_chute(self):
        """Verify prediction with confidence < 0.70 is barred from automated sorting and diverted to Bin 4."""
        uid = f"cmd_lowconf_{uuid.uuid4().hex[:6]}"
        payload = {
            "item_label": "Ambiguous Foil Packet",
            "detected_category": "Plastic Waste",
            "confidence": 0.58, # Below 0.70 threshold
            "is_fallback": False,
            "event_id": uid
        }
        resp = client.post("/api/iot/sorting/command", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["event_id"] == uid
        assert data["status"] == "diverted_to_reject"
        assert data["bin_index"] == 4
        assert data["target_bin"] == "bin_4_reject_chute"
        assert "below safety threshold" in data["rejection_reason"].lower()

    def test_fallback_heuristic_strictly_diverted_to_reject_chute(self):
        """
        Verify that fallback heuristic predictions (even with calculated confidence > 0.70)
        are barred from automated high-speed actuation and diverted to manual review chute.
        """
        uid = f"cmd_fallback_{uuid.uuid4().hex[:6]}"
        payload = {
            "item_label": "Fallback Cardboard Estimate",
            "detected_category": "Cardboard",
            "confidence": 0.82,
            "is_fallback": True, # Fallback active!
            "event_id": uid
        }
        resp = client.post("/api/iot/sorting/command", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["event_id"] == uid
        assert data["status"] == "diverted_to_reject"
        assert data["bin_index"] == 4
        assert data["target_bin"] == "bin_4_reject_chute"
        assert "fallback heuristic prediction strictly barred" in data["rejection_reason"].lower()

    def test_emergency_stop_halts_all_diverters(self):
        """Verify activating emergency stop prevents all pneumatic diverters from firing."""
        IoTSortingSafetyService.set_emergency_stop(True)

        uid = f"cmd_estop_{uuid.uuid4().hex[:6]}"
        payload = {
            "item_label": "Clean Banana Peel",
            "detected_category": "Organic Waste",
            "confidence": 0.98,
            "is_fallback": False,
            "event_id": uid
        }
        resp = client.post("/api/iot/sorting/command", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "emergency_stopped"
        assert data["bin_index"] == 4
        assert "emergency stop is active" in data["rejection_reason"].lower()

    def test_idempotent_event_dispatch(self):
        """Verify submitting the same event_id twice returns the cached record without duplicate physical actions."""
        uid = f"cmd_idemp_{uuid.uuid4().hex[:6]}"
        payload = {
            "item_label": "Aluminum Beverage Can",
            "detected_category": "Metal",
            "confidence": 0.91,
            "is_fallback": False,
            "event_id": uid
        }

        # First dispatch
        resp1 = client.post("/api/iot/sorting/command", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second dispatch with identical event_id
        resp2 = client.post("/api/iot/sorting/command", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()

        assert data1["event_id"] == data2["event_id"]
        assert data1["timestamp"] == data2["timestamp"]
        assert data1["status"] == data2["status"]

    def test_sorting_records_and_safety_status_endpoints(self):
        """Verify sorting records audit log and real-time safety status endpoints."""
        resp_records = client.get("/api/iot/sorting/records?limit=10")
        assert resp_records.status_code == 200
        rec_data = resp_records.json()
        assert "count" in rec_data
        assert "records" in rec_data

        resp_safety = client.get("/api/iot/sorting/safety-status")
        assert resp_safety.status_code == 200
        safety_data = resp_safety.json()
        assert "emergency_stop_active" in safety_data
        assert "actuators_online" in safety_data
        assert "confidence_threshold" in safety_data
        assert safety_data["confidence_threshold"] == 0.70
        assert "bins" in safety_data
        assert "statistics" in safety_data
