from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import random
from app.core.database import get_db
from app.models.vehicle import CollectionVehicle
from app.schemas.common_schemas import VehicleSchema

router = APIRouter(prefix="/vehicles", tags=["Collection Monitoring & Smart Fleet"])

@router.get("/", response_model=List[VehicleSchema])
def get_all_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(CollectionVehicle).all()
    # Apply minor jitter to coordinates for real-time tracking feel
    for v in vehicles:
        v.latitude = round(v.latitude + random.uniform(-0.0003, 0.0003), 4)
        v.longitude = round(v.longitude + random.uniform(-0.0003, 0.0003), 4)
        v.last_ping = datetime.utcnow()
    db.commit()
    return vehicles

@router.get("/{vehicle_code}", response_model=VehicleSchema)
def get_vehicle_by_code(vehicle_code: str, db: Session = Depends(get_db)):
    v = db.query(CollectionVehicle).filter(CollectionVehicle.vehicle_code == vehicle_code).first()
    if not v:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_code} not found")
    return v
