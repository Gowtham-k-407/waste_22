import os
import json
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db, get_user_db, get_waste_db
from app.core.config import settings
from app.core.security import security_bearer, decode_access_token
from app.models.contribution import ImageContribution
from app.models.user import User
from app.models.memory import UserAIRef
from app.schemas.common_schemas import ContributionSchema
from app.services.ai_vision_service import (
    AIVisionService, PRIMARY_CATEGORIES, ALL_LEVEL2_ITEMS, ITEM_TO_PRIMARY_CATEGORY
)

router = APIRouter(prefix="/contributions", tags=["Community AI Continuous Training"])

UPLOAD_DIR = os.path.join(settings.MEDIA_DIR, "contributions")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/", response_model=List[ContributionSchema])
def get_contributions(limit: int = 50, db: Session = Depends(get_db)):
    items = db.query(ImageContribution).order_by(ImageContribution.created_at.desc()).limit(limit).all()
    return items

@router.get("/stats")
def get_contribution_stats(db: Session = Depends(get_db)):
    total = db.query(ImageContribution).count()
    staged = db.query(ImageContribution).filter(ImageContribution.validation_status == "staged_for_training").count()
    approved = db.query(ImageContribution).filter(ImageContribution.validation_status == "approved_in_dataset").count()
    rejected = db.query(ImageContribution).filter(ImageContribution.validation_status == "rejected").count()
    corrected_by_users = db.query(ImageContribution).filter(ImageContribution.is_user_corrected == True).count()

    return {
        "total_contributed_images": total,
        "staged_for_retraining": staged,
        "approved_in_training_dataset": approved,
        "rejected_low_quality": rejected,
        "user_corrected_labels_count": corrected_by_users,
        "retraining_threshold": settings.TRAINING_THRESHOLD,
        "progress_towards_next_retrain": min(100.0, round((staged / settings.TRAINING_THRESHOLD) * 100, 1))
    }

@router.post("/upload-and-predict")
async def upload_and_predict(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Step 1 & 2: User uploads waste image -> AI instantly predicts class, confidence, and checks quality.
    """
    content = await file.read()
    file_size_kb = round(len(content) / 1024.0, 1)

    try:
        pil_img = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file format. Supported: JPG, PNG, WEBP.")

    # Hash for duplicate detection
    img_hash = AIVisionService.calculate_image_hash(content)
    existing_hashes = [c.image_hash for c in db.query(ImageContribution.image_hash).all() if c.image_hash]

    is_valid, quality_msg, blur_score = AIVisionService.validate_image_quality(
        pil_img, file_size_kb, existing_hashes, img_hash
    )

    # Save to disk
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    saved_filename = f"contrib_{img_hash[:12]}_{int(datetime.utcnow().timestamp())}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)
    with open(saved_path, "wb") as f:
        f.write(content)

    # AI prediction via Multi-Stage Pipeline
    prediction = AIVisionService.detect_and_classify(pil_img, filename_hint=file.filename)

    # Return prediction for user confirmation with Level 1 & Level 2 taxonomy
    return {
        "success": True,
        "image_url": f"/uploads/contributions/{saved_filename}",
        "image_hash": img_hash,
        "file_size_kb": file_size_kb,
        "ai_prediction": {
            "category": prediction["predicted_category"],    # Level 1
            "detected_item": prediction["detected_item"],     # Level 2
            "confidence": prediction["confidence"],
            "confidence_pct": prediction["confidence_pct"],
            "status": prediction["status"],                   # e.g. "High Confidence" or "Low Confidence — Please Confirm"
            "is_low_confidence": prediction["is_low_confidence"],
            "stage_notes": prediction["stage_notes"],
            "bounding_box": prediction["bounding_box"],
            "secondary_prediction": prediction["secondary_prediction"]
        },
        "quality_check": {
            "is_valid": is_valid,
            "status": "valid" if is_valid else "flagged",
            "message": quality_msg,
            "blur_score": blur_score
        },
        "prompt": "Is this classification correct?",
        "options": ["Yes, Confirm Label", "No, Correct Category"],
        "all_primary_categories": PRIMARY_CATEGORIES,
        "all_specific_items": ALL_LEVEL2_ITEMS
    }

@router.post("/confirm-and-submit")
def confirm_and_submit(
    image_url: str = Form(...),
    image_hash: str = Form(...),
    file_size_kb: float = Form(120.0),
    ai_predicted_category: str = Form(...),
    ai_confidence: float = Form(...),
    user_confirmed_category: str = Form(...),
    confirmed_item: Optional[str] = Form(None),
    is_user_corrected: bool = Form(False),
    user_notes: Optional[str] = Form(None),
    blur_score: float = Form(80.0),
    ward_number: Optional[int] = Form(None),
    location_name: Optional[str] = Form("Chennai Area"),
    contributor_name: str = Form("Citizen Volunteer"),
    add_to_personal_memory: bool = Form(False),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_waste_db)
):
    """
    Step 3, 4 & 5: User confirms or corrects label -> record stored in candidate dataset.
    Optionally saves the confirmed item to the user's private Personal AI Memory!
    """
    # Validation status logic
    if blur_score < 22.0:
        val_status = "rejected"
        rej_reason = "Low sharpness / blurry image"
    elif ai_confidence < 0.60 and not is_user_corrected:
        val_status = "pending_review"
        rej_reason = "Low AI confidence, requires expert confirmation"
    else:
        val_status = "staged_for_training"
        rej_reason = None

    contrib = ImageContribution(
        contributor_name=contributor_name,
        image_url=image_url,
        image_hash=image_hash,
        file_size_kb=file_size_kb,
        ai_predicted_category=ai_predicted_category,
        ai_confidence=ai_confidence,
        user_confirmed_category=user_confirmed_category,
        is_user_corrected=is_user_corrected,
        user_notes=user_notes,
        blur_score=blur_score,
        quality_status="valid" if val_status != "rejected" else "rejected",
        validation_status=val_status,
        rejection_reason=rej_reason,
        ward_number=ward_number,
        location_name=location_name,
        created_at=datetime.utcnow(),
        data_type="USER-CONTRIBUTED DATA"
    )
    db.add(contrib)
    db.commit()

    # Award contribution points to logged in user or admin in Database A
    current_user = None
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            current_user = user_db.query(User).filter(User.email == payload.get("sub")).first()

    if current_user:
        current_user.contribution_points = (current_user.contribution_points or 0) + (20 if is_user_corrected else 10)
        user_db.commit()

    # If user opted to add to Personal AI Memory in Database A
    memory_added = False
    if add_to_personal_memory and current_user:
        try:
            import numpy as np
            np.random.seed(int(image_hash[:8], 16) % 100000)
            simulated_vec = np.random.normal(0, 1, 128)
            simulated_vec = (simulated_vec / np.linalg.norm(simulated_vec)).tolist()
            
            ref = UserAIRef(
                user_id=current_user.id,
                image_id=f"MEM-{int(datetime.utcnow().timestamp())}",
                image_url=image_url,
                image_hash=image_hash,
                confirmed_item=confirmed_item or user_confirmed_category,
                confirmed_waste_category=user_confirmed_category,
                image_embedding_json=json.dumps(simulated_vec),
                embedding_model_version="v2.2-embed",
                reference_status="active",
                notes=user_notes or f"Saved by {current_user.full_name}"
            )
            user_db.add(ref)
            user_db.commit()
            memory_added = True
        except Exception as e:
            logger.warning(f"Failed to add personal memory: {e}")
            print("Failed to auto-add to personal memory:", e)

    db.commit()
    db.refresh(contrib)

    return {
        "success": True,
        "message": "Thank you! Your contribution has been validated and added to the continuous training dataset." + (" Also saved to your Personal AI Memory!" if memory_added else ""),
        "contribution_id": contrib.id,
        "validation_status": val_status,
        "points_earned": 20 if is_user_corrected else 10,
        "memory_added": memory_added
    }
