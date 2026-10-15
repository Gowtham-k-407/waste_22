import json
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from PIL import Image
from io import BytesIO

from app.core.database import get_db, get_user_db, get_waste_db
from app.core.security import security_bearer, decode_access_token
from app.models.detection import AIDetection
from app.models.user import User
from app.models.memory import UserAIRef
from app.models.complaint import AIInferenceAudit
from app.schemas.common_schemas import AIDetectionSchema
from app.services.ai_vision_service import AIVisionService

router = APIRouter(prefix="/detections", tags=["Smart Garbage Truck AI Detection"])

@router.get("/", response_model=List[AIDetectionSchema])
def get_recent_detections(
    vehicle_code: Optional[str] = None,
    ward_number: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_waste_db)
):
    query = db.query(AIDetection)
    if vehicle_code:
        query = query.filter(AIDetection.vehicle_code == vehicle_code)
    if ward_number:
        query = query.filter(AIDetection.ward_number == ward_number)
    
    detections = query.order_by(AIDetection.timestamp.desc()).limit(limit).all()
    results = []
    for d in detections:
        bbox = json.loads(d.bounding_box_json) if d.bounding_box_json else [0.2, 0.2, 0.8, 0.8]
        results.append(AIDetectionSchema(
            id=d.id,
            detection_code=d.detection_code,
            vehicle_code=d.vehicle_code,
            ward_number=d.ward_number,
            location_name=d.location_name,
            latitude=d.latitude,
            longitude=d.longitude,
            waste_category=d.waste_category,
            confidence=d.confidence,
            bounding_box=bbox,
            image_url=d.image_url,
            model_version=d.model_version,
            estimated_weight_kg=d.estimated_weight_kg,
            bin_fill_level_pct=d.bin_fill_level_pct,
            timestamp=d.timestamp,
            data_type=d.data_type
        ))
    return results

@router.post("/live-detect")
async def live_webcam_detect(
    file: UploadFile = File(...),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    user_db: Session = Depends(get_user_db),
    waste_db: Session = Depends(get_waste_db)
):
    """
    Core Multi-Stage AI Inference Engine:
    1. Global AI Object Detection & Hierarchical Classification (Level 1: Category, Level 2: Specific Item)
    2. Dense 128-d Visual Feature Embedding Extraction
    3. Private Personal AI Memory Search (if user authenticated)
    4. Combined Explainable Decision Fusion
    """
    content = await file.read()
    try:
        pil_img = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image frame format.")

    # 1. Global AI Multi-stage Detection
    analysis = AIVisionService.detect_and_classify(pil_img, filename_hint=file.filename or "")
    current_embedding = analysis["embedding"]

    # 2. Check for Authenticated User & Personal AI Memory Search
    personal_match = None
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            user = user_db.query(User).filter(User.email == payload.get("sub")).first()
            if user:
                # Query ONLY current user's active references in Database A (strict privacy isolation)
                user_refs = user_db.query(UserAIRef).filter(
                    UserAIRef.user_id == user.id,
                    UserAIRef.reference_status == "active"
                ).all()

                best_sim = 0.0
                best_ref = None
                for ref in user_refs:
                    try:
                        ref_vec = json.loads(ref.image_embedding_json)
                        sim = AIVisionService.calculate_cosine_similarity(current_embedding, ref_vec)
                        if sim > best_sim:
                            best_sim = sim
                            best_ref = ref
                    except Exception:
                        continue

                # If similarity >= 0.70 (70%)
                if best_sim >= 0.70 and best_ref is not None:
                    sim_pct = int(best_sim * 100)
                    personal_match = {
                        "has_match": True,
                        "reference_id": best_ref.id,
                        "previous_item": best_ref.confirmed_item,
                        "waste_category": best_ref.confirmed_waste_category,
                        "similarity": best_sim,
                        "similarity_pct": sim_pct,
                        "image_url": best_ref.image_url,
                        "date_saved": best_ref.created_at.strftime("%b %d, %Y") if best_ref.created_at else "Previously",
                        "explainable_message": f"✓ Similar to an item you previously showed me: {best_ref.confirmed_item} ({sim_pct}% match)"
                    }

    # 3. Combined Verdict
    global_conf = analysis["confidence"]
    if personal_match and personal_match["has_match"]:
        # Weighted combination: 70% Global + 30% Personal Memory
        combined_score = round(0.70 * global_conf + 0.30 * personal_match["similarity"], 2)
        combined_item = personal_match["previous_item"] if personal_match["similarity"] >= 0.85 else analysis["detected_item"]
        combined_category = personal_match["waste_category"] if personal_match["similarity"] >= 0.85 else analysis["predicted_category"]
        
        if analysis["is_low_confidence"]:
            guidance = f"The global AI model has low confidence ({int(global_conf*100)}%), but this object strongly resembles an item you previously confirmed ({personal_match['similarity_pct']}% similarity)."
        else:
            guidance = f"The current object is visually similar to an item you previously confirmed as a {personal_match['previous_item']}."
    else:
        combined_score = global_conf
        combined_item = analysis["detected_item"]
        combined_category = analysis["predicted_category"]
        guidance = "Standard Municipal AI detection model applied."

    return {
        "success": True,
        "global_detection": {
            "detected_item": analysis["detected_item"],
            "waste_category": analysis["predicted_category"],
            "confidence": global_conf,
            "confidence_pct": analysis["confidence_pct"],
            "status": analysis["status"],
            "is_low_confidence": analysis["is_low_confidence"],
            "stage_notes": analysis["stage_notes"]
        },
        "personal_ai_memory": personal_match,
        "combined_verdict": {
            "detected_item": combined_item,
            "waste_category": combined_category,
            "confidence": combined_score,
            "confidence_pct": int(combined_score * 100),
            "guidance_message": guidance
        },
        "bounding_box": analysis.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
        "secondary_prediction": analysis.get("secondary_prediction", {"predicted_category": "Mixed Waste", "confidence": 0.20}),
        "embedding": analysis.get("embedding", []),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/simulate-truck-scan")
async def simulate_truck_scan(
    vehicle_code: str = Form("GC-14"),
    ward_number: int = Form(102),
    location_name: str = Form("Royapuram High Road"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    filename = file.filename if file else "camera_frame.jpg"
    if file:
        content = await file.read()
        pil_img = Image.open(BytesIO(content))
    else:
        pil_img = Image.new('RGB', (320, 240), color=(73, 109, 137))

    analysis = AIVisionService.detect_and_classify(pil_img, filename_hint=filename)

    det = AIDetection(
        detection_code=f"DET-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        vehicle_code=vehicle_code,
        ward_number=ward_number,
        location_name=location_name,
        latitude=13.0827,
        longitude=80.2707,
        waste_category=f"{analysis['detected_item']} ({analysis['predicted_category']})",
        confidence=analysis["confidence"],
        bounding_box_json=json.dumps(analysis["bounding_box"]),
        image_url="/assets/samples/waste_sample.jpg",
        model_version="v2.2-ewaste",
        estimated_weight_kg=analysis["estimated_weight_kg"],
        bin_fill_level_pct=72.0,
        timestamp=datetime.utcnow(),
        data_type="AI-DETECTED DATA"
    )
    db.add(det)
    db.commit()
    db.refresh(det)

    return {
        "success": True,
        "detection_code": det.detection_code,
        "detected_item": analysis["detected_item"],
        "waste_category": analysis["predicted_category"],
        "confidence": det.confidence,
        "status": analysis["status"],
        "bounding_box": analysis["bounding_box"],
        "estimated_weight_kg": det.estimated_weight_kg,
        "timestamp": det.timestamp.isoformat(),
        "message": "Truck AI Camera classified object with Level 1 & Level 2 multi-stage hierarchy."
    }
