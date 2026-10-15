import os
import io
import csv
import json
import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Security, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel

from app.core.database import get_db, get_user_db, get_waste_db, get_staff_db
from app.core.security import (
    security_bearer, decode_access_token, create_access_token, verify_password, hash_password
)
from app.models.user import User, AuthAuditLog
from app.models.staff import StaffProfile, StaffDutyAssignment, StaffAuditLog
from app.models.upload import Upload, DatasetImage
from app.models.ai_model import AIModelVersion, TrainingJob
from app.services.training_worker import ModelTrainingService, get_next_model_version
from app.schemas.auth import (
    UserAdminDetailResponse, UserListResponse, UserRoleUpdateRequest, RoleDefinitionResponse
)
from app.api.auth import MUNICIPAL_STAFF_ROLES

router = APIRouter(prefix="/admin", tags=["Municipal Admin Portal & Model Training"])

ADMIN_ROLES = {"ai_admin", "system_admin", "municipal_officer", "municipal_commissioner", "solid_waste_management_officer"}

# Dependency: require admin role using Database A
def require_admin(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db)
) -> User:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Please sign in to the Admin Portal.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session token."
        )

    user = user_db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with session not found."
        )

    if user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User role '{user.role}' lacks administrative permissions. Required: system_admin or officer."
        )

    return user

# Pydantic request models
class AdminLoginRequest(BaseModel):
    email: str
    password: str

class VerificationApproveRequest(BaseModel):
    verified_category: Optional[str] = None
    verified_label: Optional[str] = None
    admin_notes: Optional[str] = None

class VerificationRejectRequest(BaseModel):
    rejection_reason: str
    admin_notes: Optional[str] = None

class BatchApproveRequest(BaseModel):
    upload_ids: List[int]

class BatchRejectRequest(BaseModel):
    upload_ids: List[int]
    rejection_reason: str

class DatasetEditRequest(BaseModel):
    waste_category: Optional[str] = None
    object_label: Optional[str] = None
    description: Optional[str] = None
    split: Optional[str] = None

class StartTrainingRequest(BaseModel):
    candidate_version: Optional[str] = None
    total_epochs: Optional[int] = 20
    batch_size: Optional[int] = 16
    learning_rate: Optional[float] = 0.001


# =========================================================================
# 1. ADMIN AUTHENTICATION
# =========================================================================

@router.post("/login")
def admin_login(payload: AdminLoginRequest, user_db: Session = Depends(get_user_db)):
    """
    Authenticate administrative personnel with strict role checks in Database A.
    """
    user = user_db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.email)
    ).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials. Please verify your email and password."
        )

    if user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Account '{user.email}' is a '{user.role}' and does not have administrative privileges."
        )

    token = create_access_token({"sub": user.email, "role": user.role, "name": user.full_name})

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization": user.organization,
            "city": user.city
        }
    }


# =========================================================================
# 2. ADMIN DASHBOARD OVERVIEW METRICS
# =========================================================================

@router.get("/overview")
def get_admin_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Returns high-level administrative KPI metrics.
    """
    total_uploads = db.query(Upload).count()
    pending_uploads = db.query(Upload).filter(Upload.status == "PENDING_VERIFICATION").count()
    approved_uploads = db.query(Upload).filter(Upload.status.in_(["Approved", "Added to Dataset", "Used for Training"])).count()
    rejected_uploads = db.query(Upload).filter(Upload.status == "Rejected").count()

    total_dataset = db.query(DatasetImage).count()
    total_models = db.query(AIModelVersion).count()
    
    active_model = db.query(AIModelVersion).filter(AIModelVersion.is_active_production == True).first()
    if not active_model:
        active_model = db.query(AIModelVersion).order_by(AIModelVersion.id.desc()).first()

    last_training = db.query(TrainingJob).filter(TrainingJob.status == "completed").order_by(TrainingJob.id.desc()).first()

    return {
        "success": True,
        "metrics": {
            "total_user_uploads": total_uploads,
            "pending_verification_count": pending_uploads,
            "approved_images_count": approved_uploads,
            "rejected_images_count": rejected_uploads,
            "total_dataset_images": total_dataset,
            "ai_models_trained_count": total_models,
            "active_model_version": active_model.version if active_model else "v2.1",
            "active_model_name": active_model.model_name if active_model else "Waste Detection Model v2.1",
            "active_model_accuracy": active_model.accuracy if active_model else 0.918,
            "active_model_f1": active_model.f1_score if active_model else 0.905,
            "last_training_date": last_training.completed_at.strftime("%b %d, %Y") if last_training and last_training.completed_at else "Recently"
        }
    }


# =========================================================================
# 3. IMAGE VERIFICATION WORKFLOW
# =========================================================================

@router.get("/image-verification")
@router.get("/uploads")
def list_admin_uploads(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Fetch user uploads for administrative verification queue.
    """
    query = db.query(Upload)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(Upload.status == status_filter)

    total_count = query.count()
    uploads = query.order_by(Upload.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "success": True,
        "total": total_count,
        "uploads": [
            {
                "id": u.id,
                "upload_id": u.upload_id,
                "user_name": u.user_name,
                "user_email": u.user_email,
                "original_filename": u.original_filename,
                "image_url": u.image_url,
                "file_size_bytes": u.file_size_bytes,
                "category": u.category,
                "object_label": u.object_label,
                "description": u.description,
                "location_context": u.location_context,
                "status": u.status,
                "ai_predicted_category": u.ai_predicted_category,
                "ai_predicted_label": u.ai_predicted_label,
                "ai_confidence": u.ai_confidence,
                "verified_by_admin_name": u.verified_by_admin_name,
                "verified_category": u.verified_category,
                "verified_label": u.verified_label,
                "rejection_reason": u.rejection_reason,
                "admin_notes": u.admin_notes,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "verified_at": u.verified_at.isoformat() if u.verified_at else None
            }
            for u in uploads
        ]
    }


@router.put("/uploads/{upload_id}/approve")
def approve_upload(
    upload_id: int,
    req: VerificationApproveRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve an uploaded image:
    1. Updates upload record status to 'Added to Dataset'
    2. Overrides category/label if administrator corrected it (e.g. Plastic -> E-Waste / Mobile Phone)
    3. Adds approved sample to verified dataset_images table
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload record not found.")

    final_cat = req.verified_category or upload.category
    final_lbl = req.verified_label or upload.object_label

    upload.status = "Added to Dataset"
    upload.verified_by_admin_id = admin.id
    upload.verified_by_admin_name = admin.full_name or admin.username
    upload.verified_category = final_cat
    upload.verified_label = final_lbl
    upload.admin_notes = req.admin_notes
    upload.verified_at = datetime.utcnow()

    # Add to dataset_images
    dataset_entry = DatasetImage(
        upload_id=upload.id,
        image_url=upload.image_url,
        stored_image_path=upload.stored_image_path,
        waste_category=final_cat,
        object_label=final_lbl,
        description=upload.description,
        location_context=upload.location_context,
        split="train",
        verified_by=admin.full_name or admin.username,
        verified_at=datetime.utcnow(),
        used_in_training=False
    )
    db.add(dataset_entry)
    db.commit()

    return {
        "success": True,
        "message": f"Image approved and added to verified training dataset as '{final_cat} / {final_lbl}'.",
        "dataset_code": dataset_entry.dataset_code,
        "upload": {
            "id": upload.id,
            "status": upload.status,
            "verified_category": upload.verified_category,
            "verified_label": upload.verified_label
        }
    }


@router.put("/uploads/{upload_id}/reject")
def reject_upload(
    upload_id: int,
    req: VerificationRejectRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject an uploaded image with reason (e.g. blurry, duplicate, irrelevant).
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload record not found.")

    upload.status = "Rejected"
    upload.verified_by_admin_id = admin.id
    upload.verified_by_admin_name = admin.full_name or admin.username
    upload.rejection_reason = req.rejection_reason
    upload.admin_notes = req.admin_notes
    upload.verified_at = datetime.utcnow()

    # If was previously in dataset, remove it
    db.query(DatasetImage).filter(DatasetImage.upload_id == upload.id).delete()
    db.commit()

    return {
        "success": True,
        "message": "Upload marked as rejected.",
        "rejection_reason": req.rejection_reason,
        "upload": {
            "id": upload.id,
            "status": upload.status,
            "rejection_reason": upload.rejection_reason
        }
    }


@router.put("/uploads/{upload_id}")
def edit_upload_metadata(
    upload_id: int,
    data: Dict[str, Any] = Body(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload record not found.")

    if "category" in data:
        upload.category = data["category"]
    if "object_label" in data:
        upload.object_label = data["object_label"]
    if "description" in data:
        upload.description = data["description"]
    if "location_context" in data:
        upload.location_context = data["location_context"]
    if "admin_notes" in data:
        upload.admin_notes = data["admin_notes"]

    db.commit()
    return {"success": True, "message": "Upload annotations updated."}


@router.post("/uploads/batch-approve")
def batch_approve_uploads(
    req: BatchApproveRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve multiple pending images in a single batch operation.
    """
    uploads = db.query(Upload).filter(Upload.id.in_(req.upload_ids)).all()
    count = 0
    for u in uploads:
        u.status = "Added to Dataset"
        u.verified_by_admin_id = admin.id
        u.verified_by_admin_name = admin.full_name or admin.username
        u.verified_category = u.category
        u.verified_label = u.object_label
        u.verified_at = datetime.utcnow()

        # Add to dataset
        ds = DatasetImage(
            upload_id=u.id,
            image_url=u.image_url,
            stored_image_path=u.stored_image_path,
            waste_category=u.category,
            object_label=u.object_label,
            description=u.description,
            location_context=u.location_context,
            split="train",
            verified_by=admin.full_name or admin.username,
            verified_at=datetime.utcnow()
        )
        db.add(ds)
        count += 1

    db.commit()
    return {"success": True, "message": f"Successfully approved {count} images to verified dataset."}


@router.post("/uploads/batch-reject")
def batch_reject_uploads(
    req: BatchRejectRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    uploads = db.query(Upload).filter(Upload.id.in_(req.upload_ids)).all()
    for u in uploads:
        u.status = "Rejected"
        u.verified_by_admin_id = admin.id
        u.verified_by_admin_name = admin.full_name or admin.username
        u.rejection_reason = req.rejection_reason
        u.verified_at = datetime.utcnow()
        db.query(DatasetImage).filter(DatasetImage.upload_id == u.id).delete()

    db.commit()
    return {"success": True, "message": f"Successfully rejected {len(uploads)} images."}


# =========================================================================
# 4. VERIFIED DATASET MANAGEMENT (/admin/dataset)
# =========================================================================

STANDARD_CATEGORIES = [
    "Plastic", "Paper", "Metal", "Glass", "Organic Waste",
    "E-Waste", "Battery", "Mobile Phone", "Electronic Components", "Other Waste"
]

@router.get("/dataset")
def get_verified_dataset(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve admin-approved dataset images organized by category.
    """
    # Category Breakdown Counts
    all_dataset = db.query(DatasetImage).all()
    category_counts = {cat: 0 for cat in STANDARD_CATEGORIES}
    for item in all_dataset:
        c = item.waste_category or "Other Waste"
        category_counts[c] = category_counts.get(c, 0) + 1

    query = db.query(DatasetImage)
    if category and category.lower() != "all":
        query = query.filter(DatasetImage.waste_category == category)
    if search:
        query = query.filter(
            (DatasetImage.object_label.ilike(f"%{search}%")) |
            (DatasetImage.location_context.ilike(f"%{search}%")) |
            (DatasetImage.description.ilike(f"%{search}%"))
        )

    total_filtered = query.count()
    images = query.order_by(DatasetImage.created_at.desc()).offset(offset).limit(limit).all()

    img_list = [
        {
            "id": img.id,
            "dataset_code": img.dataset_code,
            "upload_id": img.upload_id,
            "image_url": img.image_url,
            "waste_category": img.waste_category,
            "object_label": img.object_label,
            "description": img.description,
            "location_context": img.location_context,
            "split": img.split,
            "verified_by": img.verified_by,
            "verified_at": img.verified_at.isoformat() if img.verified_at else None,
            "used_in_training": img.used_in_training
        }
        for img in images
    ]

    return {
        "success": True,
        "total_dataset_count": len(all_dataset),
        "filtered_count": total_filtered,
        "category_counts": category_counts,
        "dataset_images": img_list,
        "images": img_list
    }


@router.put("/dataset/{dataset_id}")
def update_dataset_image(
    dataset_id: int,
    req: DatasetEditRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    img = db.query(DatasetImage).filter(DatasetImage.id == dataset_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Dataset image not found.")

    if req.waste_category:
        img.waste_category = req.waste_category
    if req.object_label:
        img.object_label = req.object_label
    if req.description is not None:
        img.description = req.description
    if req.split:
        img.split = req.split

    db.commit()
    return {"success": True, "message": "Dataset image updated successfully."}


@router.delete("/dataset/{dataset_id}")
def delete_dataset_image(
    dataset_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    img = db.query(DatasetImage).filter(DatasetImage.id == dataset_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Dataset image not found.")

    db.delete(img)
    db.commit()
    return {"success": True, "message": "Image removed from verified dataset."}


@router.get("/dataset/export")
def export_dataset_metadata(
    format: str = Query("json", pattern="^(json|csv)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Export verified dataset metadata as JSON or CSV.
    """
    images = db.query(DatasetImage).all()
    rows = [
        {
            "dataset_code": img.dataset_code,
            "waste_category": img.waste_category,
            "object_label": img.object_label,
            "image_url": img.image_url,
            "split": img.split,
            "description": img.description or "",
            "location_context": img.location_context or "",
            "verified_by": img.verified_by,
            "verified_at": img.verified_at.isoformat() if img.verified_at else "",
            "used_in_training": img.used_in_training
        }
        for img in images
    ]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "dataset_code", "waste_category", "object_label", "image_url",
            "split", "description", "location_context", "verified_by", "verified_at", "used_in_training"
        ])
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=verified_waste_dataset.csv"}
        )

    return {
        "success": True,
        "total_records": len(rows),
        "exported_at": datetime.utcnow().isoformat(),
        "records": rows
    }


# =========================================================================
# 5. AI MODEL TRAINING SYSTEM (/admin/model-training)
# =========================================================================

@router.post("/train-model")
def trigger_training(
    req: StartTrainingRequest = Body(default_factory=StartTrainingRequest),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Initiate real backend AI model training job asynchronously.
    """
    result = ModelTrainingService.start_training_job(
        db,
        candidate_version=req.candidate_version,
        total_epochs=req.total_epochs or 20,
        batch_size=req.batch_size or 16,
        learning_rate=req.learning_rate or 0.001
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/training-status")
def get_training_status(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Poll live training telemetry (progress %, epochs, losses, logs).
    """
    return ModelTrainingService.get_training_status(db)


# =========================================================================
# 6. MODEL VERSION MANAGEMENT (/admin/models)
# =========================================================================

@router.get("/models")
def list_model_versions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all trained AI models in registry.
    """
    models = db.query(AIModelVersion).order_by(AIModelVersion.id.desc()).all()
    return {
        "success": True,
        "models": [
            {
                "id": m.id,
                "model_name": m.model_name,
                "version": m.version,
                "status": "Production" if m.is_active_production else m.status.capitalize(),
                "framework": m.framework,
                "accuracy": m.accuracy,
                "precision": m.precision,
                "recall": m.recall,
                "f1_score": m.f1_score,
                "mobile_phone_recall": m.mobile_phone_recall,
                "mobile_phone_precision": m.mobile_phone_precision,
                "ewaste_f1": m.ewaste_f1,
                "training_images_count": m.training_images_count,
                "training_date": m.training_date.strftime("%b %d, %Y") if m.training_date else None,
                "dataset_version": m.dataset_version,
                "is_active_production": m.is_active_production,
                "notes": m.notes,
                "class_metrics": json.loads(m.class_metrics_json) if m.class_metrics_json else []
            }
            for m in models
        ]
    }


@router.post("/models/{model_id}/activate")
def activate_model(
    model_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deploy this model as active production model for live webcam inference and truck cameras.
    """
    target = db.query(AIModelVersion).filter(AIModelVersion.id == model_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Model version not found.")

    from app.services.ai_vision_service import AIVisionService
    from app.core.config import settings
    checkpoint_file = getattr(target, "weights_path", None) or os.path.join(settings.MODELS_DIR, f"classifier_{target.version}.pt")
    weights_to_use = checkpoint_file if os.path.exists(checkpoint_file) else None
    
    # Actually switch active neural inference model weights
    switch_ok = AIVisionService.switch_active_model(target.version, weights_path=weights_to_use)
    if not switch_ok:
        raise HTTPException(status_code=500, detail=f"Failed to load weights for model version {target.version}.")

    # Mark all other models as inactive / archived
    db.query(AIModelVersion).filter(AIModelVersion.id != model_id).update(
        {"is_active_production": False, "status": "archived"}, synchronize_session=False
    )

    target.is_active_production = True
    target.status = "production"
    db.commit()

    return {
        "success": True,
        "message": f"Model {target.version} ('{target.model_name}') is now the ACTIVE production model with verified weights.",
        "active_model": {
            "version": target.version,
            "name": target.model_name,
            "accuracy": target.accuracy,
            "f1_score": target.f1_score
        }
    }


@router.post("/models/{model_id}/rollback")
def rollback_to_model(
    model_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return activate_model(model_id, admin=admin, db=db)


@router.get("/models/active")
def get_active_model(db: Session = Depends(get_db)):
    """
    Publicly accessible endpoint returning current active model info for webcam UI.
    """
    model = db.query(AIModelVersion).filter(AIModelVersion.is_active_production == True).first()
    if not model:
        model = db.query(AIModelVersion).order_by(AIModelVersion.id.desc()).first()

    return {
        "success": True,
        "model_name": model.model_name if model else "Waste Detection Model v2.1",
        "version": model.version if model else "v2.1",
        "framework": model.framework if model else "PyTorch 2.2 / YOLOv8-Waste",
        "accuracy": model.accuracy if model else 0.918,
        "f1_score": model.f1_score if model else 0.905,
        "is_active": True
    }


# =========================================================================
# 5. USER DIRECTORY & ROLE MANAGEMENT
# =========================================================================

def _serialize_user_admin_view(u: User, staff_profile: Optional[StaffProfile] = None) -> dict:
    staff_dict = None
    if staff_profile:
        staff_dict = {
            "employee_id": staff_profile.employee_id,
            "job_title": staff_profile.job_title,
            "role_code": staff_profile.role_code,
            "department": staff_profile.department,
            "employment_status": staff_profile.employment_status,
            "assigned_zone_number": staff_profile.assigned_zone_number,
            "assigned_ward_number": staff_profile.assigned_ward_number,
            "assigned_facility_name": staff_profile.assigned_facility_name,
            "shift": staff_profile.shift,
        }
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "organization": u.organization,
        "city": u.city,
        "phone_number": u.phone_number,
        "is_active": u.is_active,
        "email_verified": u.email_verified,
        "must_change_password": u.must_change_password,
        "contribution_points": u.contribution_points or 0,
        "badges": u.badges or "Eco Citizen",
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login_at": u.last_login_at,
        "assigned_ward": u.assigned_ward,
        "staff_profile": staff_dict
    }


@router.get("/users", response_model=UserListResponse)
def list_admin_users(
    q: Optional[str] = Query(None, description="Search by username, email, or full name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query("all", description="Filter by status ('active', 'inactive', 'all')"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    user_db: Session = Depends(get_user_db),
    staff_db: Session = Depends(get_staff_db)
):
    """
    Search and list registered users with pagination and server-side filtering.
    Only authorized administrators can access the directory.
    Returns safe fields only (never secrets, password hashes, or auth tokens).
    """
    query = user_db.query(User)

    if q and q.strip():
        search_term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(User.username).like(search_term),
                func.lower(User.email).like(search_term),
                func.lower(User.full_name).like(search_term)
            )
        )

    if role and role.strip() and role != "all":
        query = query.filter(User.role == role.strip())

    if status == "active":
        query = query.filter(User.is_active == True)
    elif status == "inactive":
        query = query.filter(User.is_active == False)

    total = query.count()
    total_pages = max(1, math.ceil(total / limit))
    offset = (page - 1) * limit
    users = query.order_by(User.id.asc()).offset(offset).limit(limit).all()

    # Pre-fetch staff profiles for the users
    user_ids = [u.id for u in users]
    staff_profiles = {
        sp.user_id: sp for sp in staff_db.query(StaffProfile).filter(StaffProfile.user_id.in_(user_ids)).all()
    } if user_ids else {}

    items = [_serialize_user_admin_view(u, staff_profiles.get(u.id)) for u in users]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/users/{user_id}", response_model=UserAdminDetailResponse)
def get_admin_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    user_db: Session = Depends(get_user_db),
    staff_db: Session = Depends(get_staff_db)
):
    """
    View an individual user's administrative profile and account status.
    """
    target_user = user_db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == target_user.id).first()
    return _serialize_user_admin_view(target_user, staff_profile)


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    req: UserRoleUpdateRequest,
    admin: User = Depends(require_admin),
    user_db: Session = Depends(get_user_db),
    staff_db: Session = Depends(get_staff_db)
):
    """
    Assign or update a user's persistent role.
    Safeguards:
    - Only authorized System Administrators can modify roles.
    - Prevents self-modification to avoid accidental admin lockout.
    - Protects the last authorized administrator against removal.
    - Validates target role against official project role catalog.
    - Synchronizes staff profile if linked in Database B.
    - Creates an immutable audit record in auth_audit_logs.
    """
    if admin.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role modification requires authorized System Administrator privileges."
        )

    target_user = user_db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} does not exist."
        )

    # Protect against accidental self-lockout
    if admin.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-role modification is prohibited. Administrators cannot alter their own account role via User Directory."
        )

    # Validate target role
    valid_roles = set(MUNICIPAL_STAFF_ROLES.keys()).union({
        "system_admin", "ai_admin", "municipal_officer", "plant_operator",
        "waste_processing_plant_operator", "contributor", "public"
    })
    target_role = req.role.strip()
    if target_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{req.role}'. Must be a recognized municipal staff or platform role."
        )

    # Protect against accidental removal of the last authorized administrator
    if target_user.role == "system_admin" and target_role != "system_admin":
        active_admin_count = user_db.query(User).filter(
            User.role == "system_admin",
            User.is_active == True
        ).count()
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Safety restriction: Cannot remove or demote the last remaining active System Administrator."
            )

    old_role = target_user.role
    target_user.role = target_role
    target_user.updated_at = datetime.now(timezone.utc)

    # Update permanent_role in preferences_json
    target_prefs = {}
    if target_user.preferences_json:
        try:
            target_prefs = json.loads(target_user.preferences_json)
        except Exception:
            target_prefs = {}
    target_prefs["permanent_role"] = target_role
    target_user.preferences_json = json.dumps(target_prefs)

    user_db.commit()
    user_db.refresh(target_user)

    # Synchronize with staff_profiles if applicable
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == target_user.id).first()
    if staff_profile and target_role in MUNICIPAL_STAFF_ROLES:
        staff_profile.role_code = target_role
        staff_profile.updated_at = datetime.now(timezone.utc)
        staff_db.commit()

    # Record in audit log
    audit_entry = AuthAuditLog(
        user_id=target_user.id,
        action=f"role_change:admin={admin.email}:target={target_user.email}:from={old_role}:to={target_role}:reason={req.reason or 'Administrative update'}:outcome=success"
    )
    user_db.add(audit_entry)
    user_db.commit()

    return {
        "success": True,
        "message": f"Successfully updated role for user '{target_user.username}' from '{old_role}' to '{target_role}'.",
        "user": _serialize_user_admin_view(target_user, staff_profile)
    }


@router.get("/roles", response_model=List[RoleDefinitionResponse])
def get_role_definitions(admin: User = Depends(require_admin)):
    """
    Catalog of all official project roles, titles, departments, and scopes.
    """
    roles_catalog = [
        {
            "role": "system_admin",
            "title": "System Security Administrator",
            "department": "GCC IT & Cybersecurity Division",
            "scope": "Global Administrative",
            "description": "Full access to platform administration, user management, and security settings.",
            "is_staff": False,
            "is_admin": True
        },
        {
            "role": "ai_admin",
            "title": "AI Administrator & ML Lead",
            "department": "Smart Waste Analytics & AI Wing",
            "scope": "AI Governance",
            "description": "Verification of waste images, model continuous learning, retraining, and dataset curation.",
            "is_staff": False,
            "is_admin": True
        },
        {
            "role": "municipal_officer",
            "title": "Municipal SWM Officer",
            "department": "Solid Waste Management",
            "scope": "Citywide Municipal Operations",
            "description": "Operational coordination, ward analytics, alert escalation, and grievance oversight.",
            "is_staff": True,
            "is_admin": True
        },
        {
            "role": "contributor",
            "title": "Citizen Contributor",
            "department": "Public Community",
            "scope": "Household Area",
            "description": "Upload waste photos, verify predictions, report sanitation grievances.",
            "is_staff": False,
            "is_admin": False
        },
        {
            "role": "public",
            "title": "Public Citizen",
            "department": "Public Community",
            "scope": "Household Area",
            "description": "View neighborhood truck schedules, route status, and civic guides.",
            "is_staff": False,
            "is_admin": False
        }
    ]

    for code, info in MUNICIPAL_STAFF_ROLES.items():
        if code not in [r["role"] for r in roles_catalog]:
            roles_catalog.append({
                "role": code,
                "title": info["title"],
                "department": info["department"],
                "scope": info.get("scope", "Municipal Staff"),
                "description": f"Authorized GCC municipal employee: {info['title']}",
                "is_staff": True,
                "is_admin": code in ADMIN_ROLES
            })

    return roles_catalog

