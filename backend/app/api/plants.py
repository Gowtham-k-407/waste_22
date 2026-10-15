from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db, get_user_db, get_staff_db
from app.core.security import get_current_user_from_token
from app.core.rbac import verify_facility_scope
from app.models.user import User, AuthAuditLog
from app.models.facility import SegregationPlant
from app.schemas.common_schemas import PlantSchema

router = APIRouter(prefix="/plants", tags=["Segregation & Recycling Plants"])

PLANT_VIEW_ROLES = {
    "system_admin", "assistant_engineer", "environmental_engineer",
    "solid_waste_management_officer", "waste_processing_plant_operator",
    "plant_operator", "municipal_commissioner", "municipal_officer",
    "waste_disposal_facility_supervisor", "waste_weighbridge_operator",
    "waste_management_project_manager", "municipal_control_room_operator"
}

@router.get("/", response_model=List[PlantSchema])
def get_plants(
    status: Optional[str] = Query(None, pattern="^(active|inactive|maintenance)"),
    facility_type: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user.role not in PLANT_VIEW_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Access restricted. Segregation plant operational metrics are reserved for municipal plant engineers and operators. Citizens may use /api/public/nearby-facilities."
        )
    query = db.query(SegregationPlant)
    if status:
        query = query.filter(SegregationPlant.status == status)
    if facility_type:
        query = query.filter(SegregationPlant.facility_type.ilike(f"%{facility_type}%"))

    plants = query.all()
    results = []
    for p in plants:
        util = round((p.current_input_tpd / p.capacity_tpd * 100), 1) if p.capacity_tpd > 0 else 0.0
        results.append(PlantSchema(
            id=p.id,
            name=p.name,
            facility_type=p.facility_type,
            latitude=p.latitude,
            longitude=p.longitude,
            capacity_tpd=p.capacity_tpd,
            current_input_tpd=p.current_input_tpd,
            utilization_pct=util,
            status=p.status,
            accepted_categories=p.accepted_categories,
            operator_name=p.operator_name,
            contact_phone=p.contact_phone,
            address=p.address
        ))
    return results

@router.put("/{plant_id}/status")
def update_plant_status(
    plant_id: int,
    status: str,
    current_input: Optional[float] = None,
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_db)
):
    PLANT_STATUS_ROLES = {
        "system_admin", "assistant_engineer", "environmental_engineer",
        "solid_waste_management_officer", "waste_processing_plant_operator",
        "plant_operator", "municipal_commissioner", "municipal_officer"
    }
    if current_user.role not in PLANT_STATUS_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: Role '{current_user.role}' lacks authority to modify plant operating status."
        )

    plant = db.query(SegregationPlant).filter(SegregationPlant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    # Enforce facility scope for operators
    verify_facility_scope(current_user, plant_id, staff_db)

    plant.status = status
    if current_input is not None:
        plant.current_input_tpd = current_input
    db.commit()

    # Log audit event
    audit = AuthAuditLog(
        user_id=current_user.id,
        action=f"plant_status_updated:{plant.name}:{status}"
    )
    user_db.add(audit)
    user_db.commit()

    return {"success": True, "message": f"Plant {plant.name} updated to {status}"}
