from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from datetime import datetime

from pydantic import BaseModel, Field
from app.core.database import get_db, get_user_db
from app.core.rbac import require_roles
from app.models.user import User, AuthAuditLog
from app.models.iot import IoTDevice, DeviceTelemetry, IoTSortingRecord
from app.services.mqtt_service import process_telemetry_payload, get_connection_status
from app.services.iot_simulator import IoTSimulatorService
from app.services.iot_sorting_service import IoTSortingSafetyService

router = APIRouter(prefix="/iot", tags=["IoT & Fleet Telemetry"])

@router.get("/status")
@router.get("/broker-status")
def get_iot_broker_status(db: Session = Depends(get_db)):
    """
    Returns live Adafruit IO MQTT broker connection health, message counts,
    active feeds, and device indicators.
    """
    conn = get_connection_status()
    total_devices = db.query(IoTDevice).count()
    online_devices = db.query(IoTDevice).filter(IoTDevice.status == "online").count()
    real_devices = db.query(IoTDevice).filter(IoTDevice.is_simulated == False).count()

    return {
        "adafruit_io": conn,
        "device_summary": {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "real_hardware_devices": real_devices,
            "simulated_devices": total_devices - real_devices
        },
        "description": "Adafruit IO MQTT over TLS (Port 8883) for Smart Waste Bins, Scales & Telemetry"
    }

@router.get("/devices")
def list_devices(
    device_type: Optional[str] = None,
    is_simulated: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(IoTDevice)
    if device_type:
        query = query.filter(IoTDevice.device_type == device_type)
    if is_simulated is not None:
        query = query.filter(IoTDevice.is_simulated == is_simulated)

    devices = query.order_by(IoTDevice.last_seen_at.desc()).all()

    result = []
    for d in devices:
        # Get latest telemetry reading
        latest = db.query(DeviceTelemetry).filter(
            DeviceTelemetry.device_id == d.device_id
        ).order_by(DeviceTelemetry.timestamp.desc()).first()

        result.append({
            "device_id": d.device_id,
            "name": d.name,
            "device_type": d.device_type,
            "ward_number": d.ward_number,
            "zone_number": d.zone_number,
            "status": d.status,
            "battery_level": d.battery_level,
            "is_simulated": d.is_simulated,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            "latest_reading": {
                "timestamp": latest.timestamp.isoformat() if latest else None,
                "bin_fill_pct": latest.bin_fill_pct if latest else None,
                "weight_kg": latest.weight_kg if latest else None,
                "latitude": latest.latitude if latest else None,
                "longitude": latest.longitude if latest else None,
                "speed_kmh": latest.speed_kmh if latest else None,
                "sensor_status": latest.sensor_status if latest else "NORMAL",
                "data_source": latest.data_source if latest else ("simulated_iot" if d.is_simulated else "live_mqtt")
            } if latest else None
        })
    return {"devices": result, "count": len(result)}


@router.get("/devices/{device_id}/telemetry")
def get_device_telemetry(
    device_id: str,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db)
):
    records = db.query(DeviceTelemetry).filter(
        DeviceTelemetry.device_id == device_id
    ).order_by(DeviceTelemetry.timestamp.desc()).limit(limit).all()

    return {
        "device_id": device_id,
        "count": len(records),
        "telemetry": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "latitude": r.latitude,
                "longitude": r.longitude,
                "bin_fill_pct": r.bin_fill_pct,
                "weight_kg": r.weight_kg,
                "temperature_c": r.temperature_c,
                "humidity_pct": r.humidity_pct,
                "battery_pct": r.battery_pct,
                "speed_kmh": r.speed_kmh,
                "sensor_status": r.sensor_status,
                "is_simulated": r.is_simulated,
                "data_source": r.data_source
            }
            for r in reversed(records)
        ]
    }


@router.post("/telemetry")
def ingest_telemetry_webhook(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Direct HTTP ingestion webhook for sensor devices lacking direct MQTT connection.
    Validates payload against standard IoT schema.
    """
    device_id = payload.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="Missing required 'device_id' in payload.")

    result = process_telemetry_payload(device_id, payload, is_simulated=payload.get("is_simulated", False))
    return result


ADMIN_IOT_ROLES = ["system_admin", "municipal_officer", "ai_admin"]

@router.post("/simulator/start")
def start_simulator(
    interval_seconds: float = Query(15.0, ge=2.0, le=120.0),
    current_user: User = Depends(require_roles(ADMIN_IOT_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    result = IoTSimulatorService.start(interval_seconds=interval_seconds)
    audit = AuthAuditLog(user_id=current_user.id, action="iot_simulator_started")
    user_db.add(audit)
    user_db.commit()
    return result


@router.post("/simulator/stop")
def stop_simulator(
    current_user: User = Depends(require_roles(ADMIN_IOT_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    result = IoTSimulatorService.stop()
    audit = AuthAuditLog(user_id=current_user.id, action="iot_simulator_stopped")
    user_db.add(audit)
    user_db.commit()
    return result


@router.get("/simulator/status")
def get_simulator_status():
    return {
        "running": IoTSimulatorService.is_running(),
        "mode": "SIMULATED DATA" if IoTSimulatorService.is_running() else "STANDBY"
    }


# -------------------------------------------------------------
# IoT PHYSICAL SORTING CONVEYOR & SAFETY CONTROLS
# -------------------------------------------------------------
class SortingCommandRequest(BaseModel):
    item_label: Optional[str] = "Detected Item"
    detected_category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_fallback: Optional[bool] = False
    prediction_id: Optional[str] = None
    event_id: Optional[str] = None

class EmergencyStopRequest(BaseModel):
    active: bool

@router.post("/sorting/command")
def execute_sorting_command(
    cmd: SortingCommandRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a waste detection to the physical sorting layer.
    Enforces safety rules:
      - Emergency Stop halts all mechanical action.
      - Fallback & low confidence (<0.70) predictions are safely diverted to Bin 4 (Manual Review Chute).
      - Category-to-bin destination mapping.
      - Optical break-beam sensor confirmation loop.
    """
    record = IoTSortingSafetyService.evaluate_and_dispatch(
        db=db,
        item_label=cmd.item_label,
        detected_category=cmd.detected_category,
        confidence=cmd.confidence,
        is_fallback=cmd.is_fallback or False,
        prediction_id=cmd.prediction_id,
        event_id=cmd.event_id
    )
    return {
        "event_id": record.event_id,
        "prediction_id": record.prediction_id,
        "item_label": record.item_label,
        "detected_category": record.detected_category,
        "confidence": record.confidence,
        "is_fallback": record.is_fallback,
        "target_bin": record.target_bin,
        "bin_index": record.bin_index,
        "status": record.status,
        "rejection_reason": record.rejection_reason,
        "actuator_id": record.actuator_id,
        "actuator_latency_ms": record.actuator_latency_ms,
        "verified_destination": record.verified_destination,
        "sensor_verification_status": record.sensor_verification_status,
        "timestamp": record.created_at.isoformat()
    }

@router.get("/sorting/records")
def list_sorting_records(
    limit: int = Query(50, le=500),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns recent physical sorting execution audit records."""
    query = db.query(IoTSortingRecord)
    if status:
        query = query.filter(IoTSortingRecord.status == status)
    records = query.order_by(IoTSortingRecord.created_at.desc()).limit(limit).all()
    return {
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "event_id": r.event_id,
                "prediction_id": r.prediction_id,
                "item_label": r.item_label,
                "detected_category": r.detected_category,
                "confidence": r.confidence,
                "is_fallback": r.is_fallback,
                "target_bin": r.target_bin,
                "bin_index": r.bin_index,
                "status": r.status,
                "rejection_reason": r.rejection_reason,
                "actuator_id": r.actuator_id,
                "actuator_latency_ms": r.actuator_latency_ms,
                "sensor_verification_status": r.sensor_verification_status,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]
    }

@router.post("/sorting/emergency-stop")
def toggle_emergency_stop(
    req: EmergencyStopRequest,
    current_user: User = Depends(require_roles(ADMIN_IOT_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    """
    Emergency Stop override for automated sorting line.
    Immediately halts diverters and diverts conveyor belt flow to reject chute.
    """
    is_active = IoTSortingSafetyService.set_emergency_stop(req.active)
    action_str = "iot_sorting_emergency_stop_activated" if req.active else "iot_sorting_emergency_stop_cleared"
    audit = AuthAuditLog(user_id=current_user.id, action=action_str)
    user_db.add(audit)
    user_db.commit()
    return {
        "emergency_stop_active": is_active,
        "status": "STOPPED" if is_active else "OPERATIONAL",
        "message": "Emergency Stop engaged! Automated actuators locked." if is_active else "Emergency Stop cleared. Resuming normal sorting."
    }

@router.get("/sorting/safety-status")
def get_sorting_safety_status(db: Session = Depends(get_db)):
    """Returns real-time status of sorting line safety, actuators, and reject rate statistics."""
    return IoTSortingSafetyService.get_system_status(db)

