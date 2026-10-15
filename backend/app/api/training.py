from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.orm import Session
from app.core.database import get_db, get_user_db
from app.core.security import get_current_user_from_token
from app.core.rbac import require_roles
from app.models.user import User, AuthAuditLog
from app.services.training_service import TrainingService

router = APIRouter(prefix="/ai-training", tags=["Continuous AI Retraining Pipeline"])

ADMIN_TRAINING_ROLES = ["system_admin", "ai_admin"]

@router.get("/status")
def get_training_status(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: AI training status is restricted to municipal engineering and administration."
        )
    return TrainingService.get_training_progress(db)

@router.post("/trigger-retraining")
def trigger_retraining(
    force: bool = Form(False),
    current_user: User = Depends(require_roles(ADMIN_TRAINING_ROLES)),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_db)
):
    result = TrainingService.trigger_retraining(db, force=force)
    
    # Audit log
    audit = AuthAuditLog(
        user_id=current_user.id,
        action="ai_retraining_triggered"
    )
    user_db.add(audit)
    user_db.commit()

    return result

@router.get("/class-distribution")
def get_class_distribution():
    return TrainingService.get_class_distribution()

@router.get("/confusion-matrix")
def get_confusion_matrix():
    return TrainingService.get_confusion_matrix()
