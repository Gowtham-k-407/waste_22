import time
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.core.config import settings
from app.services import mqtt_service
from app.services.mqtt_service import (
    process_telemetry_payload,
    get_connection_status,
    on_aio_connect,
    on_aio_message,
    on_aio_disconnect,
    publish_to_feed,
    _connection_state
)
from app.core.database import WasteSessionLocal
from app.models.iot import IoTDevice, DeviceTelemetry


class TestAdafruitIOMQTT:
    """
    Automated unit & integration test suite for Adafruit IO MQTT.
    Uses mocked Paho MQTT client; does not require live broker credentials.
    """

    def test_01_configuration_defaults(self):
        assert settings.ADAFRUIT_IO_HOST == "io.adafruit.com"
        assert settings.ADAFRUIT_IO_PORT == 8883
        assert settings.ADAFRUIT_IO_USE_TLS is True
        assert len(settings.ADAFRUIT_IO_FEEDS) >= 3

    def test_02_connection_status_unconfigured(self):
        with patch.object(settings, "ADAFRUIT_IO_USERNAME", ""):
            status = get_connection_status()
            assert status["configured"] is False
            assert status["status"] in ("offline", "unconfigured")

    def test_03_mock_successful_connect(self):
        mock_client = MagicMock()
        _connection_state["is_connected"] = False
        on_aio_connect(mock_client, None, None, 0)
        assert _connection_state["is_connected"] is True
        assert _connection_state["last_connected_at"] is not None
        mock_client.subscribe.assert_called()

    def test_04_mock_connection_failure(self):
        mock_client = MagicMock()
        on_aio_connect(mock_client, None, None, 5) # rc=5: Not authorized
        assert _connection_state["is_connected"] is False
        assert _connection_state["last_error"] is not None

    def test_05_mock_disconnect(self):
        mock_client = MagicMock()
        _connection_state["is_connected"] = True
        on_aio_disconnect(mock_client, None, 0)
        assert _connection_state["is_connected"] is False
        assert _connection_state["last_disconnected_at"] is not None

    def test_06_incoming_scalar_feed_payload(self):
        mock_msg = MagicMock()
        mock_msg.topic = f"{settings.ADAFRUIT_IO_USERNAME or 'testuser'}/feeds/wastedash-bin-fill"
        mock_msg.payload = b"78.5"

        on_aio_message(None, None, mock_msg)
        status = get_connection_status()
        assert status["last_message_at"] is not None

        # Verify Database C record
        db = WasteSessionLocal()
        try:
            record = db.query(DeviceTelemetry).filter(
                DeviceTelemetry.device_id == "AIO-WASTEDASH-BIN-FILL"
            ).order_by(DeviceTelemetry.timestamp.desc()).first()
            assert record is not None
            assert record.bin_fill_pct == 78.5
            assert record.is_simulated is False
            assert record.data_source == "adafruit_io_mqtt"
        finally:
            db.close()

    def test_07_incoming_json_feed_payload(self):
        mock_msg = MagicMock()
        mock_msg.topic = f"{settings.ADAFRUIT_IO_USERNAME or 'testuser'}/feeds/wastedash-telemetry"
        payload_data = {
            "message_id": "TEST-MSG-001",
            "device_id": "BIN-TEST-AIO-01",
            "bin_fill_pct": 82.0,
            "weight_kg": 45.2,
            "distance_cm": 18.0,
            "temperature_c": 31.5,
            "humidity_pct": 68.0
        }
        mock_msg.payload = json.dumps(payload_data).encode("utf-8")

        on_aio_message(None, None, mock_msg)

        db = WasteSessionLocal()
        try:
            device = db.query(IoTDevice).filter(IoTDevice.device_id == "AIO-WASTEDASH-TELEMETRY").first()
            assert device is not None
        finally:
            db.close()

    def test_08_out_of_range_and_invalid_values_clamped(self):
        # Fill > 100% must clamp to 100%
        res = process_telemetry_payload("TEST-CLAMP", {"bin_fill_pct": 145.0, "battery_pct": -10.0, "weight_kg": -5.0})
        assert res["success"] is True

        db = WasteSessionLocal()
        try:
            t = db.query(DeviceTelemetry).filter(DeviceTelemetry.device_id == "TEST-CLAMP").order_by(DeviceTelemetry.id.desc()).first()
            assert t.bin_fill_pct == 100.0
            assert t.battery_pct == 0.0
            assert t.weight_kg == 0.0
        finally:
            db.close()

    def test_09_duplicate_message_prevention(self):
        p1 = {"message_id": "UNIQUE-DEDUP-001", "bin_fill_pct": 50.0}
        res1 = process_telemetry_payload("TEST-DEDUP", p1)
        assert res1["success"] is True

        # Exact duplicate message ID
        res2 = process_telemetry_payload("TEST-DEDUP", p1)
        assert res2["success"] is False
        assert res2["status"] == "duplicate_ignored"

    def test_10_stale_telemetry_indicator(self):
        # Set last message to 10 minutes ago
        _connection_state["last_message_at"] = datetime.utcnow() - timedelta(minutes=10)
        status = get_connection_status()
        assert status["is_stale"] is True

        # Set last message to 1 minute ago
        _connection_state["last_message_at"] = datetime.utcnow() - timedelta(minutes=1)
        status = get_connection_status()
        assert status["is_stale"] is False

    def test_11_simulation_independent_of_mqtt(self):
        # Telemetry from simulation carries is_simulated=True and data_source="simulated_iot"
        sim_res = process_telemetry_payload("SIM-BIN-01", {"bin_fill_pct": 60.0}, is_simulated=True)
        assert sim_res["is_simulated"] is True

        db = WasteSessionLocal()
        try:
            sim_record = db.query(DeviceTelemetry).filter(DeviceTelemetry.device_id == "SIM-BIN-01").order_by(DeviceTelemetry.id.desc()).first()
            assert sim_record.is_simulated is True
            assert sim_record.data_source == "simulated_iot"
        finally:
            db.close()

    def test_12_publish_to_feed_fails_safely_when_disconnected(self):
        _connection_state["is_connected"] = False
        res = publish_to_feed("test-feed", 42.0)
        assert res["success"] is False
        assert "not connected" in res["error"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
