import time
import math
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List

from app.services.mqtt_service import process_telemetry_payload

logger = logging.getLogger("wastedash.simulator")

_simulator_thread: threading.Thread = None
_simulator_running: bool = False

SIMULATED_DEVICES = [
    {
        "device_id": "BIN-ZN08-W102",
        "name": "Anna Nagar 2nd Avenue Commercial Smart Bin",
        "device_type": "smart_bin",
        "ward_number": 102,
        "zone_number": 8,
        "base_lat": 13.0850,
        "base_lng": 80.2150,
        "base_fill": 45.0,
        "fill_rate": 2.5
    },
    {
        "device_id": "BIN-ZN09-W118",
        "name": "T. Nagar Panagal Park Public Smart Bin",
        "device_type": "smart_bin",
        "ward_number": 118,
        "zone_number": 9,
        "base_lat": 13.0410,
        "base_lng": 80.2330,
        "base_fill": 68.0,
        "fill_rate": 4.0
    },
    {
        "device_id": "BIN-ZN13-W173",
        "name": "Besant Nagar Beach Promenade Smart Bin",
        "device_type": "smart_bin",
        "ward_number": 173,
        "zone_number": 13,
        "base_lat": 12.9980,
        "base_lng": 80.2720,
        "base_fill": 32.0,
        "fill_rate": 1.8
    },
    {
        "device_id": "TRUCK-GC01-TRACKER",
        "name": "Smart Compactor Truck GC-01 GPS Telemetry",
        "device_type": "vehicle_tracker",
        "ward_number": 105,
        "zone_number": 8,
        "base_lat": 13.0825,
        "base_lng": 80.2110,
        "base_speed": 22.0
    },
    {
        "device_id": "TRUCK-GC02-TRACKER",
        "name": "Smart Compactor Truck GC-02 GPS Telemetry",
        "device_type": "vehicle_tracker",
        "ward_number": 115,
        "zone_number": 9,
        "base_lat": 13.0450,
        "base_lng": 80.2380,
        "base_speed": 18.5
    }
]

def _simulation_loop(interval_seconds: float = 15.0):
    global _simulator_running
    step = 0
    logger.info("Deterministic IoT Simulator thread started.")

    while _simulator_running:
        step += 1
        now_iso = datetime.utcnow().isoformat() + "Z"

        for dev in SIMULATED_DEVICES:
            d_id = dev["device_id"]
            d_type = dev["device_type"]
            
            if d_type == "smart_bin":
                # Deterministic sinusoidal fill oscillation
                fill = round(min(98.0, max(10.0, dev["base_fill"] + 15.0 * math.sin(step * 0.2))), 1)
                distance_cm = round(max(5.0, 100.0 - fill), 1)
                weight_kg = round(fill * 0.45, 1)

                payload = {
                    "message_id": f"SIM-{d_id}-{uuid.uuid4().hex[:6]}",
                    "device_type": "smart_bin",
                    "name": dev["name"],
                    "ward_number": dev["ward_number"],
                    "zone_number": dev["zone_number"],
                    "latitude": dev["base_lat"],
                    "longitude": dev["base_lng"],
                    "bin_fill_pct": fill,
                    "distance_cm": distance_cm,
                    "weight_kg": weight_kg,
                    "temperature_c": round(29.5 + 2.0 * math.sin(step * 0.1), 1),
                    "humidity_pct": round(65.0 + 5.0 * math.cos(step * 0.1), 1),
                    "battery_pct": round(max(40.0, 95.0 - (step * 0.05)), 1),
                    "sensor_status": "NORMAL" if fill < 85.0 else "NEAR_CAPACITY_ALERT",
                    "timestamp": now_iso
                }
            else:
                # Vehicle GPS movement along route
                offset_lat = 0.003 * math.sin(step * 0.15)
                offset_lng = 0.003 * math.cos(step * 0.15)
                lat = round(dev["base_lat"] + offset_lat, 5)
                lng = round(dev["base_lng"] + offset_lng, 5)

                payload = {
                    "message_id": f"SIM-{d_id}-{uuid.uuid4().hex[:6]}",
                    "device_type": "vehicle_tracker",
                    "name": dev["name"],
                    "ward_number": dev["ward_number"],
                    "zone_number": dev["zone_number"],
                    "latitude": lat,
                    "longitude": lng,
                    "speed_kmh": round(max(5.0, dev["base_speed"] + 4.0 * math.sin(step * 0.3)), 1),
                    "heading_deg": round((step * 15) % 360, 1),
                    "battery_pct": 98.0,
                    "sensor_status": "NORMAL",
                    "timestamp": now_iso
                }

            # Ingest through the exact same processing pipeline as real MQTT!
            process_telemetry_payload(d_id, payload, is_simulated=True)

        time.sleep(interval_seconds)

    logger.info("Deterministic IoT Simulator thread stopped.")


class IoTSimulatorService:
    @staticmethod
    def is_running() -> bool:
        global _simulator_running
        return _simulator_running

    @staticmethod
    def start(interval_seconds: float = 15.0):
        global _simulator_thread, _simulator_running
        if _simulator_running:
            return {"status": "already_running"}

        _simulator_running = True
        _simulator_thread = threading.Thread(target=_simulation_loop, args=(interval_seconds,), daemon=True)
        _simulator_thread.start()
        return {"status": "started", "devices_count": len(SIMULATED_DEVICES), "interval_seconds": interval_seconds}

    @staticmethod
    def stop():
        global _simulator_running
        _simulator_running = False
        return {"status": "stopped"}

    @staticmethod
    def trigger_single_step():
        """Immediately generates and ingests one deterministic telemetry cycle."""
        _simulation_loop(interval_seconds=0.01)
        return {"status": "single_cycle_ingested"}
