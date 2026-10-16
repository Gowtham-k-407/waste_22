from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from app.core.database import Base

class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False) # e.g. BIN-ZONE8-01, TRUCK-GC01
    device_type = Column(String, default="smart_bin", index=True) # smart_bin, vehicle_tracker, plant_sensor
    name = Column(String, nullable=False)
    ward_number = Column(Integer, nullable=True)
    zone_number = Column(Integer, nullable=True)
    status = Column(String, default="offline", index=True) # online, offline, degraded
    battery_level = Column(Float, nullable=True)
    firmware_version = Column(String, default="1.0.0")
    is_simulated = Column(Boolean, default=False, index=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("iot_devices.device_id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Waste & Fill Observations
    bin_fill_pct = Column(Float, nullable=True)
    distance_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    
    # Environmental & Telemetry Sensors
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    battery_pct = Column(Float, nullable=True)
    speed_kmh = Column(Float, nullable=True)
    heading_deg = Column(Float, nullable=True)
    
    # Status & Provenance
    sensor_status = Column(String, default="NORMAL") # NORMAL, TILT_ALERT, LID_OPEN, FAULT
    is_simulated = Column(Boolean, default=False, index=True)
    data_source = Column(String, default="live_mqtt") # live_mqtt, simulated_iot, http_ingest
    raw_payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IoTSortingRecord(Base):
    __tablename__ = "iot_sorting_records"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False) # Idempotent identifier
    prediction_id = Column(String, index=True, nullable=True)
    item_label = Column(String, nullable=False) # e.g. "Plastic Waste", "Organic Waste"
    detected_category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    is_fallback = Column(Boolean, default=False)
    
    # Destination & Routing
    target_bin = Column(String, nullable=False) # "bin_1_organic", "bin_2_recyclables", "bin_3_scrap_ewaste", "bin_4_reject_chute"
    bin_index = Column(Integer, nullable=False) # 1, 2, 3, 4
    
    # Execution & Safety
    status = Column(String, nullable=False, index=True) # "executed", "diverted_to_reject", "blocked_safety", "emergency_stopped"
    rejection_reason = Column(String, nullable=True)
    actuator_id = Column(String, default="PNEUMATIC_ARM_01")
    actuator_latency_ms = Column(Float, default=45.0)
    
    # Verified physical feedback loop
    verified_destination = Column(String, nullable=True) # sensor confirmation e.g. "bin_1_organic"
    sensor_verification_status = Column(String, default="unverified") # "verified", "mismatch", "timeout", "unverified"
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

