import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from PIL import Image
from io import BytesIO

from app.core.config import settings
from app.core.database import get_db, get_user_db, get_waste_db
from app.core.security import security_bearer, decode_access_token
from app.models.upload import Upload
from app.models.user import User
from app.services.ai_vision_service import AIVisionService

router = APIRouter(prefix="/uploads", tags=["User Dataset Uploads"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024 # 15 MB

@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_user_waste_image(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    object_label: Optional[str] = Form(None),
    objectName: Optional[str] = Form(None),
    object_name: Optional[str] = Form(None),
    category: Optional[str] = Form("Unknown"),
    description: Optional[str] = Form(None),
    location_context: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_waste_db)
):
    """
    Upload a waste image with metadata to help improve municipal AI models.
    Supports multipart form with 'file' or 'image' and 'object_label' or 'objectName'.
    Validates file format (JPG, PNG, WEBP) and size (<= 15MB).
    Runs automated pre-classification and stages image with status PENDING_VERIFICATION.
    """
    actual_file = file or image
    if not actual_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided. Please attach an image file using 'file' or 'image'."
        )

    actual_label = (object_label or objectName or object_name or "").strip()
    if not actual_label:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object name is required. Example: Mobile Phone, Plastic Bottle, Battery, E-Waste."
        )

    actual_category = (category or "Unknown").strip()
    actual_desc = (description or "").strip()
    actual_location = (location_context or location or "Chennai Municipal Area").strip()

    # 1. Format & Extension validation
    content_type = actual_file.content_type.lower() if actual_file.content_type else ""
    filename = actual_file.filename or "waste_image.jpg"
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    if ext == "jpeg":
        ext = "jpg"

    if content_type not in ALLOWED_MIME_TYPES and ext not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type ({content_type}). Allowed formats: JPG, JPEG, PNG, WEBP."
        )

    # Read content & size validation
    content = await actual_file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 15MB (Received {file_size / (1024*1024):.2f} MB)."
        )

    # Image integrity check with PIL
    try:
        pil_img = Image.open(BytesIO(content))
        pil_img.verify()
        pil_img = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid image file. Please upload a clear photo."
        )

    # 2. Save file permanently to storage
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    unique_name = f"user_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    stored_path = os.path.join(settings.MEDIA_DIR, unique_name)
    with open(stored_path, "wb") as f:
        f.write(content)

    # Relative public URL
    image_url = f"/uploads/{unique_name}"

    # 3. Determine User ID & Name
    user_id = None
    user_name = "Citizen Contributor"
    user_email = None

    if auth and auth.credentials:
        try:
            payload = decode_access_token(auth.credentials)
            if payload and payload.get("sub"):
                user = user_db.query(User).filter(User.email == payload.get("sub")).first()
                if user:
                    user_id = user.id
                    user_name = user.full_name or user.username
                    user_email = user.email
        except Exception:
            pass

    # 4. Automated AI Pre-Classification
    try:
        ai_result = AIVisionService.detect_and_classify(pil_img, filename_hint=filename)
        ai_cat = ai_result.get("predicted_category", actual_category)
        ai_lbl = ai_result.get("detected_item", actual_label)
        ai_conf = ai_result.get("confidence", 0.85)
    except Exception:
        ai_cat = actual_category
        ai_lbl = actual_label
        ai_conf = 0.50

    # 5. Persist Upload record
    upload_record = Upload(
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        original_filename=filename,
        stored_image_path=stored_path,
        image_url=image_url,
        file_size_bytes=file_size,
        mime_type=content_type or f"image/{ext}",
        category=actual_category,
        object_label=actual_label,
        description=actual_desc,
        location_context=actual_location,
        status="PENDING_VERIFICATION",
        ai_predicted_category=ai_cat,
        ai_predicted_label=ai_lbl,
        ai_confidence=ai_conf,
        created_at=datetime.utcnow()
    )

    db.add(upload_record)
    db.commit()
    db.refresh(upload_record)

    res_payload = {
        "id": upload_record.id,
        "upload_id": upload_record.upload_id,
        "imageUrl": upload_record.image_url,
        "image_url": upload_record.image_url,
        "original_filename": upload_record.original_filename,
        "status": "PENDING_VERIFICATION",
        "category": upload_record.category,
        "object_label": upload_record.object_label,
        "objectName": upload_record.object_label,
        "description": upload_record.description,
        "location_context": upload_record.location_context,
        "ai_predicted_category": upload_record.ai_predicted_category,
        "ai_predicted_label": upload_record.ai_predicted_label,
        "ai_confidence": upload_record.ai_confidence,
        "created_at": upload_record.created_at.isoformat()
    }

    return {
        "success": True,
        "message": "Image uploaded successfully and is waiting for admin verification",
        "upload": res_payload,
        "data": res_payload
    }


@router.get("")
@router.get("/")
def get_user_uploads(
    status_filter: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_waste_db)
):
    """
    Retrieve list of uploaded images from Database C.
    If authenticated, returns user's uploads. If admin, returns all or user's.
    """
    query = db.query(Upload)

    current_user = None
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            current_user = user_db.query(User).filter(User.email == payload.get("sub")).first()

    # If not admin, restrict to current user's uploads
    if current_user and current_user.role not in ["ai_admin", "system_admin", "municipal_officer"]:
        query = query.filter(Upload.user_id == current_user.id)
    elif not current_user:
        # For public/guest view, return latest public community uploads
        pass

    if status_filter:
        query = query.filter(Upload.status == status_filter)

    uploads = query.order_by(Upload.created_at.desc()).limit(100).all()

    return {
        "success": True,
        "count": len(uploads),
        "uploads": [
            {
                "id": u.id,
                "upload_id": u.upload_id,
                "user_name": u.user_name,
                "original_filename": u.original_filename,
                "image_url": u.image_url,
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
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "verified_at": u.verified_at.isoformat() if u.verified_at else None
            }
            for u in uploads
        ]
    }


@router.get("/{upload_id}")
def get_upload_detail(
    upload_id: int,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")

    current_user = None
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            current_user = user_db.query(User).filter(User.email == payload.get("sub")).first()

    is_admin = current_user and current_user.role in ["ai_admin", "system_admin", "municipal_officer", "municipal_commissioner", "solid_waste_management_officer"]
    is_owner = current_user and upload.user_id == current_user.id

    # If the upload is private/pending/rejected and requester is neither owner nor admin, deny access
    if not (is_admin or is_owner):
        if upload.status != "APPROVED_FOR_TRAINING":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this private upload record."
            )
        # For public approved uploads, mask personal email and internal admin notes
        user_email_val = None
        admin_notes_val = None
    else:
        user_email_val = upload.user_email
        admin_notes_val = upload.admin_notes

    return {
        "id": upload.id,
        "upload_id": upload.upload_id,
        "user_name": upload.user_name,
        "user_email": user_email_val,
        "original_filename": upload.original_filename,
        "image_url": upload.image_url,
        "file_size_bytes": upload.file_size_bytes,
        "category": upload.category,
        "object_label": upload.object_label,
        "description": upload.description,
        "location_context": upload.location_context,
        "status": upload.status,
        "ai_predicted_category": upload.ai_predicted_category,
        "ai_predicted_label": upload.ai_predicted_label,
        "ai_confidence": upload.ai_confidence,
        "verified_by_admin_name": upload.verified_by_admin_name,
        "verified_category": upload.verified_category,
        "verified_label": upload.verified_label,
        "rejection_reason": upload.rejection_reason,
        "admin_notes": admin_notes_val,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "verified_at": upload.verified_at.isoformat() if upload.verified_at else None
    }
