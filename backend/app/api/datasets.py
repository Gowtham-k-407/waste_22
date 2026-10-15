from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db, get_user_db
from app.core.rbac import require_roles
from app.models.user import User, AuthAuditLog
from app.services.data_connector_service import DataConnectorService

router = APIRouter(prefix="/datasets", tags=["Dataset Management & Connectors"])

DATASET_ROLES = ["system_admin", "ai_admin", "waste_management_data_analyst", "municipal_officer"]

@router.get("/catalog")
def get_sources():
    return DataConnectorService.get_catalog()

@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    source_name: str = Form("Custom Municipal Upload"),
    current_user: User = Depends(require_roles(DATASET_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    if not file.filename.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files supported for automated schema normalization.")
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    result = DataConnectorService.normalize_csv_content(text)

    audit = AuthAuditLog(
        user_id=current_user.id,
        action=f"dataset_csv_uploaded:{file.filename}"
    )
    user_db.add(audit)
    user_db.commit()

    return result
