from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db, get_user_db
from app.core.rbac import require_roles
from app.models.user import User, AuthAuditLog
from app.models.iot import IoTDevice, DeviceTelemetry
from app.services.mqtt_service import process_telemetry_payload, get_connection_status
from app.services.iot_simulator import IoTSimulatorService

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
