from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random
from pydantic import BaseModel

from app.core.database import get_db, get_staff_db
from app.models.vehicle import CollectionVehicle
from app.models.user import User
from app.models.staff import StaffProfile
from app.schemas.common_schemas import VehicleSchema
from app.core.security import get_current_user_from_token
from app.core.rbac import MUNICIPAL_STAFF_ROLES, ADMIN_ROLES

router = APIRouter(prefix="/vehicles", tags=["Collection Monitoring & Smart Fleet"])

class PublicTruckResponse(BaseModel):
    assigned: bool
    vehicle_code: Optional[str] = None
    vehicle_type: Optional[str] = None
    status: str
    current_fill_pct: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_ping: Optional[datetime] = None
    assigned_ward_id: Optional[int] = None
    assigned_ward_number: Optional[int] = None
    data_mode: str # simulated, live, stale, unavailable
    is_stale: bool = False
    message: Optional[str] = None

@router.get("/assigned-truck", response_model=PublicTruckResponse)
@router.get("/assigned-truck/location", response_model=PublicTruckResponse)
def get_my_assigned_truck(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Public-safe endpoint returning ONLY the permitted collection truck information
    for the authenticated user's registered/verified municipal ward.
    Excludes driver phone, driver identity, battery/fuel telemetry, and other wards' vehicles.
    """
    verified_ward = current_user.assigned_ward
    v = db.query(CollectionVehicle).filter(CollectionVehicle.assigned_ward_id == verified_ward).first()
    if not v:
        return PublicTruckResponse(
            assigned=False,
            status="unavailable",
            data_mode="unavailable",
            assigned_ward_id=verified_ward,
            assigned_ward_number=verified_ward,
            latitude=None,
            longitude=None,
            last_ping=None,
            message=f"No collection truck is currently assigned or active in Ward {verified_ward}."
        )

    # Validate coordinate bounds
    if v.latitude is None or v.longitude is None or not (-90.0 <= v.latitude <= 90.0 and -180.0 <= v.longitude <= 180.0):
        return PublicTruckResponse(
            assigned=True,
            vehicle_code=v.vehicle_code,
            vehicle_type=v.vehicle_type,
            status="unavailable",
            data_mode="unavailable",
            assigned_ward_id=verified_ward,
            assigned_ward_number=verified_ward,
            latitude=None,
            longitude=None,
            last_ping=v.last_ping,
            message="No valid GPS coordinates available for assigned truck."
        )

    # Check staleness (if last_ping > 15 minutes)
    now = datetime.utcnow()
    last_ping_dt = v.last_ping or now
    elapsed_seconds = (now - last_ping_dt).total_seconds()
    is_stale = elapsed_seconds > 900
    data_mode = "stale" if is_stale else "simulated"

    return PublicTruckResponse(
        assigned=True,
        vehicle_code=v.vehicle_code,
        vehicle_type=v.vehicle_type,
        status=v.status,
        current_fill_pct=v.current_fill_pct,
        latitude=v.latitude,
        longitude=v.longitude,
        last_ping=v.last_ping,
        assigned_ward_id=v.assigned_ward_id,
        assigned_ward_number=v.assigned_ward_id,
        data_mode=data_mode,
        is_stale=is_stale,
        message=f"Collection truck active in Ward {verified_ward}." if not is_stale else "Last known GPS reading received >15 minutes ago."
    )


@router.get("/", response_model=List[VehicleSchema])
def get_all_vehicles(
    db: Session = Depends(get_db),
    staff_db: Session = Depends(get_staff_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Full fleet telemetry. Strictly restricted to GCC municipal staff and administrators.
    Ordinary public and contributor accounts are denied with HTTP 403.
    """
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Full city-wide fleet telemetry is restricted to municipal staff. Use /api/vehicles/assigned-truck for your area collection status."
        )

    query = db.query(CollectionVehicle)
    # If the user is ward-scoped staff, filter to their assigned ward
    if current_user.role not in ADMIN_ROLES and current_user.role != "municipal_commissioner":
        staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if staff_profile and staff_profile.assigned_ward_number:
            query = query.filter(CollectionVehicle.assigned_ward_id == staff_profile.assigned_ward_number)

    vehicles = query.all()
    # Apply minor jitter to coordinates for real-time tracking feel
    for v in vehicles:
        v.latitude = round(v.latitude + random.uniform(-0.0003, 0.0003), 4)
        v.longitude = round(v.longitude + random.uniform(-0.0003, 0.0003), 4)
        v.last_ping = datetime.utcnow()
    db.commit()
    return vehicles

@router.get("/{vehicle_code}")
def get_vehicle_by_code(
    vehicle_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    v = db.query(CollectionVehicle).filter(CollectionVehicle.vehicle_code == vehicle_code).first()
    if not v:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_code} not found")

    if current_user.role in ["public", "contributor"]:
        # Only allow viewing if assigned to user's verified ward
        if v.assigned_ward_id != current_user.assigned_ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle {vehicle_code} not found or not assigned to your verified municipal area."
            )
        # Return only public fields (no driver credentials or internal telemetry)
        now = datetime.utcnow()
        last_ping_dt = v.last_ping or now
        is_stale = (now - last_ping_dt).total_seconds() > 900
        return {
            "vehicle_code": v.vehicle_code,
            "vehicle_type": v.vehicle_type,
            "status": v.status,
            "current_fill_pct": v.current_fill_pct,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "last_ping": v.last_ping,
            "assigned_ward_id": v.assigned_ward_id,
            "data_mode": "stale" if is_stale else "simulated",
            "is_stale": is_stale
        }

    return VehicleSchema.model_validate(v)
