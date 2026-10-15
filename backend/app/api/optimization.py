from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.models.user import User
from app.models.optimization import OptimizationRecommendation
from app.schemas.common_schemas import OptimizationSchema
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/optimization", tags=["Smart Collection Optimization"])

OPTIMIZATION_ROLES = {
    "system_admin", "assistant_engineer", "environmental_engineer",
    "solid_waste_management_officer", "waste_management_coordinator",
    "municipal_commissioner", "municipal_officer", "waste_management_project_manager"
}

@router.get("/recommendations", response_model=List[OptimizationSchema])
def get_recommendations(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user.role not in OPTIMIZATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted. Solid waste route and segregation optimization models are reserved for municipal operations staff."
        )
    recs = db.query(OptimizationRecommendation).filter(OptimizationRecommendation.status == "Active").all()
    if not recs:
        # Generate on the fly
        new_recs = OptimizationService.generate_recommendations(db)
        for r in new_recs:
            obj = OptimizationRecommendation(
                recommendation_code=f"REC-{r['category'][:3].upper()}-{r.get('ward_number', 100)}",
                category=r["category"],
                ward_number=r.get("ward_number"),
                ward_name=r.get("ward_name"),
                target_plant_name=r.get("target_plant_name"),
                title=r["title"],
                description=r["description"],
                expected_benefit=r["expected_benefit"],
                confidence_score=r["confidence_score"],
                status="Active",
                tag=r["tag"]
            )
            db.add(obj)
        db.commit()
        recs = db.query(OptimizationRecommendation).filter(OptimizationRecommendation.status == "Active").all()
    return recs
