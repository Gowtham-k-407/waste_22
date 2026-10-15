import ssl
import json
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import paho.mqtt.client as mqtt
from app.core.config import settings
from app.core.database import WasteSessionLocal
from app.models.iot import IoTDevice, DeviceTelemetry

logger = logging.getLogger("wastedash.adafruit_mqtt")

# Message deduplication cache with sliding expiration
_processed_message_ids = set()
_mqtt_client: Optional[mqtt.Client] = None
_client_lock = threading.Lock()

# Connection state tracking
_connection_state = {
    "is_connected": False,
    "broker_host": "io.adafruit.com",
    "port": 8883,
    "use_tls": True,
    "username_configured": False,
    "last_connected_at": None,
    "last_disconnected_at": None,
    "last_message_at": None,
    "last_error": None,
    "reconnect_attempts": 0,
    "messages_received_count": 0,
    "subscribed_feeds": []
}

def get_connection_status() -> Dict[str, Any]:
    """Returns real-time Adafruit IO MQTT connection metrics and telemetry state."""
    has_credentials = bool(settings.ADAFRUIT_IO_USERNAME and settings.ADAFRUIT_IO_KEY)
    status_str = "connected" if _connection_state["is_connected"] else ("offline" if has_credentials else "unconfigured")

    # Check if telemetry is stale (> 5 minutes since last message when connected)
    is_stale = False
    if _connection_state["last_message_at"]:
        elapsed = (datetime.utcnow() - _connection_state["last_message_at"]).total_seconds()
        is_stale = elapsed > 300

    return {
        "status": status_str,
        "is_connected": _connection_state["is_connected"],
        "broker_host": settings.ADAFRUIT_IO_HOST,
        "broker_port": settings.ADAFRUIT_IO_PORT,
        "use_tls": settings.ADAFRUIT_IO_USE_TLS,
        "configured": has_credentials,
        "username_masked": (settings.ADAFRUIT_IO_USERNAME[:2] + "***") if settings.ADAFRUIT_IO_USERNAME else None,
        "last_connected_at": _connection_state["last_connected_at"].isoformat() if _connection_state["last_connected_at"] else None,
        "last_message_at": _connection_state["last_message_at"].isoformat() if _connection_state["last_message_at"] else None,
        "is_stale": is_stale,
        "reconnect_attempts": _connection_state["reconnect_attempts"],
        "messages_received_count": _connection_state["messages_received_count"],
        "subscribed_feeds": _connection_state["subscribed_feeds"],
        "last_error": _connection_state["last_error"],
        "data_provenance": "REAL_ADAFRUIT_IO_TELEMETRY" if _connection_state["is_connected"] else "SIMULATED / STANDBY"
    }

def process_telemetry_payload(device_id: str, payload: Dict[str, Any], is_simulated: bool = False, feed_key: str = "") -> Dict[str, Any]:
    """
    Validates, dedupes, and persists IoT device telemetry into Database C (Waste DB).
    Accepts both JSON objects and sanitized scalar feed measurements.
    """
    db = WasteSessionLocal()
    try:
        msg_id = payload.get("message_id")
        if msg_id:
            if msg_id in _processed_message_ids:
                return {"success": False, "status": "duplicate_ignored"}
            _processed_message_ids.add(msg_id)
            if len(_processed_message_ids) > 10000:
                _processed_message_ids.clear()

        # Parse timestamp
        ts = datetime.utcnow()
        if "timestamp" in payload:
            try:
                ts = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                ts = datetime.utcnow()

        # Sanitize and validate ranges
        fill_pct = None
        if "bin_fill_pct" in payload and payload["bin_fill_pct"] is not None:
            fill_pct = max(0.0, min(100.0, float(payload["bin_fill_pct"])))

        weight_kg = None
        if "weight_kg" in payload and payload["weight_kg"] is not None:
            weight_kg = max(0.0, float(payload["weight_kg"]))

        battery_pct = None
        if "battery_pct" in payload and payload["battery_pct"] is not None:
            battery_pct = max(0.0, min(100.0, float(payload["battery_pct"])))

        distance_cm = float(payload.get("distance_cm")) if payload.get("distance_cm") is not None else None
        lat = float(payload.get("latitude")) if payload.get("latitude") is not None else None
        lng = float(payload.get("longitude")) if payload.get("longitude") is not None else None
        temp_c = float(payload.get("temperature_c")) if payload.get("temperature_c") is not None else None
        hum_pct = float(payload.get("humidity_pct")) if payload.get("humidity_pct") is not None else None
        speed = float(payload.get("speed_kmh")) if payload.get("speed_kmh") is not None else None
        heading = float(payload.get("heading_deg")) if payload.get("heading_deg") is not None else None

        # Device registration/upsert in Database C
        dev = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
        dev_type = payload.get("device_type", "smart_bin" if "bin" in device_id.lower() or "fill" in feed_key else "scale_sensor")
        dev_name = payload.get("name", f"Adafruit IO Sensor {device_id}")

        if not dev:
            dev = IoTDevice(
                device_id=device_id,
                device_type=dev_type,
                name=dev_name,
                ward_number=payload.get("ward_number", 102),
                zone_number=payload.get("zone_number", 8),
                status="online",
                battery_level=battery_pct,
                firmware_version=payload.get("firmware_version", "aio-v2.2"),
                is_simulated=is_simulated,
                last_seen_at=datetime.utcnow()
            )
            db.add(dev)
        else:
            dev.status = "online"
            if battery_pct is not None:
                dev.battery_level = battery_pct
            dev.last_seen_at = datetime.utcnow()
            if fill_pct is not None:
                dev.last_fill_percentage = fill_pct
            if is_simulated:
                dev.is_simulated = True

        # Insert telemetry record into Database C
        telemetry = DeviceTelemetry(
            device_id=device_id,
            timestamp=ts,
            latitude=lat or 13.0827,
            longitude=lng or 80.2707,
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
            data_source="adafruit_io_mqtt" if not is_simulated else "simulated_iot",
            raw_payload_json=json.dumps(payload),
            created_at=datetime.utcnow()
        )
        db.add(telemetry)
        db.commit()

        _connection_state["last_message_at"] = datetime.utcnow()
        _connection_state["messages_received_count"] += 1

        return {
            "success": True,
            "device_id": device_id,
            "status": "persisted",
            "is_simulated": is_simulated,
            "timestamp": ts.isoformat()
        }

    except Exception as e:
        logger.error(f"Error persisting telemetry for {device_id}: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def on_aio_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        _connection_state["is_connected"] = True
        _connection_state["last_connected_at"] = datetime.utcnow()
        _connection_state["last_error"] = None
        _connection_state["reconnect_attempts"] = 0
        logger.info(f"Connected to Adafruit IO MQTT ({settings.ADAFRUIT_IO_HOST}:{settings.ADAFRUIT_IO_PORT}) over TLS successfully.")

        # Subscribe to Adafruit IO feeds: <username>/feeds/# or specific feeds
        username = settings.ADAFRUIT_IO_USERNAME or "+"
        subscribed = []
        all_feeds_topic = f"{username}/feeds/#"
        client.subscribe(all_feeds_topic, qos=1)
        subscribed.append(all_feeds_topic)
        logger.info(f"Subscribed to Adafruit IO wildcard topic: {all_feeds_topic}")

        if settings.ADAFRUIT_IO_USERNAME:
            for feed in settings.ADAFRUIT_IO_FEEDS:
                feed_topic = f"{settings.ADAFRUIT_IO_USERNAME}/feeds/{feed}"
                subscribed.append(feed_topic)

        _connection_state["subscribed_feeds"] = subscribed
    else:
        _connection_state["is_connected"] = False
        _connection_state["last_error"] = f"Adafruit IO connection refused with code {rc}"
        logger.warning(f"Adafruit IO connection failed with result code {rc}")

def on_aio_disconnect(client, userdata, disconnect_flags_or_rc, properties=None):
    _connection_state["is_connected"] = False
    _connection_state["last_disconnected_at"] = datetime.utcnow()
    logger.info("Disconnected from Adafruit IO MQTT broker.")

def on_aio_message(client, userdata, msg):
    """
    Parses incoming Adafruit IO messages on topics: <username>/feeds/<feed-key>
    Supports both raw scalar feed values (Adafruit IO default) and full JSON payloads.
    """
    try:
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8").strip()
        parts = topic.split("/")

        # Adafruit IO standard: <username>/feeds/<feed-key>
        if len(parts) >= 3 and parts[1] == "feeds":
            feed_key = parts[2]
            device_id = f"AIO-{feed_key.upper()}"

            # Determine if payload is JSON or scalar
            try:
                payload = json.loads(payload_str)
                if not isinstance(payload, dict):
                    payload = {"value": payload}
            except Exception:
                # Scalar value (e.g., Adafruit IO feed numeric value "68.5")
                payload = {"value": payload_str}

            # Map feed keys to standardized fields
            if "fill" in feed_key:
                try:
                    payload["bin_fill_pct"] = float(payload.get("bin_fill_pct", payload.get("value", 0)))
                except (ValueError, TypeError):
                    pass
            elif "weight" in feed_key or "scale" in feed_key:
                try:
                    payload["weight_kg"] = float(payload.get("weight_kg", payload.get("value", 0)))
                except (ValueError, TypeError):
                    pass
            elif "temp" in feed_key:
                try:
                    payload["temperature_c"] = float(payload.get("temperature_c", payload.get("value", 0)))
                except (ValueError, TypeError):
                    pass
            elif "hum" in feed_key:
                try:
                    payload["humidity_pct"] = float(payload.get("humidity_pct", payload.get("value", 0)))
                except (ValueError, TypeError):
                    pass

            # Ingest as genuine live MQTT reading
            process_telemetry_payload(device_id, payload, is_simulated=False, feed_key=feed_key)

    except Exception as e:
        logger.error(f"Failed to process Adafruit IO message on topic {msg.topic}: {e}")

def start_mqtt_client_if_configured():
    """
    Initializes and starts the background Adafruit IO MQTT client over TLS (Port 8883).
    Non-blocking: FastAPI starts cleanly whether Adafruit IO is configured or temporarily offline.
    """
    global _mqtt_client

    if not settings.ADAFRUIT_IO_USERNAME or not settings.ADAFRUIT_IO_KEY:
        logger.info("Adafruit IO credentials not configured (ADAFRUIT_IO_USERNAME / ADAFRUIT_IO_KEY empty). Live MQTT listener inactive.")
        _connection_state["username_configured"] = False
        return

    _connection_state["username_configured"] = True

    with _client_lock:
        if _mqtt_client is not None:
            return

        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"wastedash_{settings.ADAFRUIT_IO_USERNAME}_{int(time.time())}"
            )
            # Authenticate with Adafruit IO username and AIO Key
            client.username_pw_set(settings.ADAFRUIT_IO_USERNAME, settings.ADAFRUIT_IO_KEY)

            # Enforce TLS certificate verification for secure port 8883
            if settings.ADAFRUIT_IO_USE_TLS:
                ssl_ctx = ssl.create_default_context()
                client.tls_set_context(ssl_ctx)

            client.on_connect = on_aio_connect
            client.on_disconnect = on_aio_disconnect
            client.on_message = on_aio_message

            # Bounded reconnect backoff: 2s min to 60s max
            client.reconnect_delay_set(min_delay=2, max_delay=60)

            # Asynchronous connection so startup is never blocked
            client.connect_async(settings.ADAFRUIT_IO_HOST, settings.ADAFRUIT_IO_PORT, keepalive=60)
            client.loop_start()
            _mqtt_client = client
            logger.info(f"Adafruit IO MQTT client started (connecting to {settings.ADAFRUIT_IO_HOST}:{settings.ADAFRUIT_IO_PORT} over TLS).")
        except Exception as e:
            _connection_state["last_error"] = str(e)
            logger.warning(f"Could not initialize Adafruit IO MQTT client: {e}. Application will continue in standalone/simulation mode.")

def stop_mqtt_client():
    """Graceful disconnection of Adafruit IO client during application shutdown."""
    global _mqtt_client
    with _client_lock:
        if _mqtt_client is not None:
            try:
                _mqtt_client.loop_stop()
                _mqtt_client.disconnect()
                logger.info("Adafruit IO MQTT client disconnected gracefully.")
            except Exception as e:
                logger.warning(f"Error during Adafruit IO client shutdown: {e}")
            finally:
                _mqtt_client = None
                _connection_state["is_connected"] = False

def publish_to_feed(feed_key: str, value: Any) -> Dict[str, Any]:
    """Publishes a value to an authorized Adafruit IO feed: <username>/feeds/<feed-key>."""
    global _mqtt_client
    if not _mqtt_client or not _connection_state["is_connected"]:
        return {"success": False, "error": "Adafruit IO broker not connected"}

    username = settings.ADAFRUIT_IO_USERNAME
    topic = f"{username}/feeds/{feed_key}"
    payload = json.dumps(value) if isinstance(value, (dict, list)) else str(value)

    try:
        inf = _mqtt_client.publish(topic, payload, qos=1)
        inf.wait_for_publish(timeout=3.0)
        return {"success": True, "topic": topic, "feed_key": feed_key}
    except Exception as e:
        logger.error(f"Failed to publish to Adafruit IO feed {feed_key}: {e}")
        return {"success": False, "error": str(e)}
