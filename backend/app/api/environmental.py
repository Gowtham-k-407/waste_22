from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.geography import Ward
from app.services.environmental_service import EnvironmentalService

router = APIRouter(prefix="/environmental", tags=["Environmental Impact"])

@router.get("/summary")
def get_environmental_summary(db: Session = Depends(get_db)):
    wards = db.query(Ward).all()
    total_tons = sum(w.daily_waste_tons for w in wards) if wards else 5420.0
    avg_seg = sum(w.segregation_efficiency for w in wards) / len(wards) if wards else 61.4
    return EnvironmentalService.calculate_city_impact(total_tons, avg_seg)
