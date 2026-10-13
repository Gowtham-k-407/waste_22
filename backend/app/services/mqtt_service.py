import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.iot import IoTDevice, DeviceTelemetry

logger = logging.getLogger("wastedash.mqtt")

_processed_message_ids = set()
_mqtt_client: Optional[mqtt.Client] = None

def process_telemetry_payload(device_id: str, payload: Dict[str, Any], is_simulated: bool = False) -> Dict[str, Any]:
    """
    Validates, dedupes, and persists IoT device telemetry to the database.
    Used by both the live Paho MQTT listener and the deterministic IoT simulator.
    """
    db = SessionLocal()
    try:
        msg_id = payload.get("message_id")
        if msg_id:
            if msg_id in _processed_message_ids:
                return {"success": False, "status": "duplicate_ignored"}
            _processed_message_ids.add(msg_id)
            if len(_processed_message_ids) > 10000:
                _processed_message_ids.clear()

        # Parse timestamp or fallback to now
        ts = datetime.utcnow()
        if "timestamp" in payload:
            try:
                ts = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                ts = datetime.utcnow()

        # Sanitize and validate ranges
        fill_pct = None
        if "bin_fill_pct" in payload:
            fill_pct = max(0.0, min(100.0, float(payload["bin_fill_pct"])))
        
        weight_kg = None
        if "weight_kg" in payload:
            weight_kg = max(0.0, float(payload["weight_kg"]))

        battery_pct = None
        if "battery_pct" in payload:
            battery_pct = max(0.0, min(100.0, float(payload["battery_pct"])))

        distance_cm = float(payload.get("distance_cm")) if "distance_cm" in payload else None
        lat = float(payload.get("latitude")) if "latitude" in payload else None
        lng = float(payload.get("longitude")) if "longitude" in payload else None
        temp_c = float(payload.get("temperature_c")) if "temperature_c" in payload else None
        hum_pct = float(payload.get("humidity_pct")) if "humidity_pct" in payload else None
        speed = float(payload.get("speed_kmh")) if "speed_kmh" in payload else None
        heading = float(payload.get("heading_deg")) if "heading_deg" in payload else None

        # Device registration/upsert
        dev = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
        dev_type = payload.get("device_type", "smart_bin" if "bin" in device_id.lower() else "vehicle_tracker")
        dev_name = payload.get("name", f"Municipal Device {device_id}")

        if not dev:
            dev = IoTDevice(
                device_id=device_id,
                device_type=dev_type,
                name=dev_name,
                ward_number=payload.get("ward_number"),
                zone_number=payload.get("zone_number"),
                status="online",
                battery_level=battery_pct,
                firmware_version=payload.get("firmware_version", "1.0.0"),
                is_simulated=is_simulated,
                last_seen_at=datetime.utcnow()
            )
            db.add(dev)
        else:
            dev.status = "online"
            if battery_pct is not None:
                dev.battery_level = battery_pct
            dev.last_seen_at = datetime.utcnow()
            if is_simulated:
                dev.is_simulated = True

        # Insert telemetry record
        telemetry = DeviceTelemetry(
            device_id=device_id,
            timestamp=ts,
            latitude=lat,
            longitude=lng,
            bin_fill_pct=fill_pct,
            distance_cm=distance_cm,
            weight_kg=weight_kg,
            temperature_c=temp_c,
            humidity_pct=hum_pct,
            battery_pct=battery_pct,
            speed_kmh=speed,
            heading_deg=heading,
            sensor_status=payload.get("sensor_status", "NORMAL"),
            is_simulated=is_simulated,
            data_source="simulated_iot" if is_simulated else "live_mqtt",
            raw_payload_json=json.dumps(payload),
            created_at=datetime.utcnow()
        )
        db.add(telemetry)
        db.commit()

        return {
            "success": True,
            "device_id": device_id,
            "status": "persisted",
            "is_simulated": is_simulated,
            "timestamp": ts.isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing telemetry for device {device_id}: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT Broker successfully.")
        topic_pattern = f"{settings.MQTT_TOPIC_PREFIX}/devices/+/telemetry"
        client.subscribe(topic_pattern)
        logger.info(f"Subscribed to topic: {topic_pattern}")
    else:
        logger.warning(f"MQTT connect returned result code {rc}")

def on_mqtt_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        # Expected topic format: {prefix}/devices/{device_id}/telemetry
        if len(topic_parts) >= 4 and topic_parts[-1] == "telemetry":
            device_id = topic_parts[2]
            payload = json.loads(msg.payload.decode("utf-8"))
            process_telemetry_payload(device_id, payload, is_simulated=False)
    except Exception as e:
        logger.error(f"Failed to handle MQTT message on {msg.topic}: {e}")

def start_mqtt_client_if_configured():
    """Starts background MQTT client thread if MQTT_BROKER_URL is specified."""
    global _mqtt_client
    if not settings.MQTT_BROKER_URL:
        logger.info("MQTT_BROKER_URL not set. Live MQTT listener inactive (Simulator ready).")
        return

    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="wastedash_backend")
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        if settings.MQTT_TLS_ENABLED:
            client.tls_set()

        client.on_connect = on_mqtt_connect
        client.on_message = on_mqtt_message

        client.connect_async(settings.MQTT_BROKER_URL, settings.MQTT_PORT, 60)
        client.loop_start()
        _mqtt_client = client
        logger.info(f"MQTT client loop started for {settings.MQTT_BROKER_URL}:{settings.MQTT_PORT}")
    except Exception as e:
        logger.error(f"Failed to start MQTT client: {e}")
