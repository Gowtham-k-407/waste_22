import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import (
    user_engine, staff_engine, waste_engine,
    UserBase, StaffBase, WasteBase,
    engine, Base, SessionLocal
)
from app.services.seed_service import seed_all_databases
from app.services.simulation_engine import SimulationEngine

# Import routers
from app.api import (
    auth, dashboard, waste, wards, plants,
    vehicles, detections, contributions,
    training, models, datasets, optimization,
    alerts, environmental, simulation, memory,
    uploads, admin_portal, iot,
    complaints, notifications, staff_portal, public_portal
)
from app.services.mqtt_service import start_mqtt_client_if_configured

# Initialize tables for all three isolated logical databases
UserBase.metadata.create_all(bind=user_engine)
StaffBase.metadata.create_all(bind=staff_engine)
WasteBase.metadata.create_all(bind=waste_engine)

# Seed all 3 databases idempotently (preserves existing data)
seed_all_databases()

# Start background MQTT client if broker is configured
start_mqtt_client_if_configured()

# Start background simulation engine if enabled
if settings.SIMULATION_MODE:
    SimulationEngine.get_instance().start(interval_seconds=float(settings.SIMULATION_TICK_SECONDS))

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.2.0",
    description="Automated Solid Waste Segregation & AI Model Continuous Improvement Dashboard for Municipal Recycling Plants (Greater Chennai Corporation)"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media static uploads
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.MEDIA_DIR), name="uploads")

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(waste.router, prefix=settings.API_V1_STR)
app.include_router(wards.router, prefix=settings.API_V1_STR)
app.include_router(plants.router, prefix=settings.API_V1_STR)
app.include_router(vehicles.router, prefix=settings.API_V1_STR)
app.include_router(detections.router, prefix=settings.API_V1_STR)
app.include_router(contributions.router, prefix=settings.API_V1_STR)
app.include_router(training.router, prefix=settings.API_V1_STR)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(datasets.router, prefix=settings.API_V1_STR)
app.include_router(optimization.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(environmental.router, prefix=settings.API_V1_STR)
app.include_router(simulation.router, prefix=settings.API_V1_STR)
app.include_router(memory.router, prefix=settings.API_V1_STR)
app.include_router(uploads.router, prefix=settings.API_V1_STR)
app.include_router(admin_portal.router, prefix=settings.API_V1_STR)
app.include_router(iot.router, prefix=settings.API_V1_STR)
app.include_router(complaints.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(staff_portal.router, prefix=settings.API_V1_STR)
app.include_router(public_portal.router, prefix=settings.API_V1_STR)

from fastapi import UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from PIL import Image
from io import BytesIO
from app.core.database import get_db
from app.models.ai_model import AIModelVersion
from app.services.ai_vision_service import AIVisionService

@app.post("/api/detect")
async def detect_frame_with_active_model(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Real-Time Webcam Waste Detection API using currently active AI Model.
    Returns bounding box coordinates, detected object name, waste category, confidence %,
    and active model information.
    """
    content = await file.read()
    try:
        pil_img = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid camera frame image format.")

    # Retrieve currently deployed active model
    active_model = db.query(AIModelVersion).filter(AIModelVersion.is_active_production == True).first()
    if not active_model:
        active_model = db.query(AIModelVersion).order_by(AIModelVersion.id.desc()).first()

    if active_model and AIVisionService._active_version != active_model.version:
        AIVisionService.switch_active_model(active_model.version)

    analysis = AIVisionService.detect_and_classify(pil_img, filename_hint=file.filename or "")

    category_colors = {
        "E-Waste": "#8B5CF6",       # Purple
        "Plastic": "#3B82F6",       # Blue
        "Metal": "#64748B",         # Gray
        "Organic Waste": "#10B981", # Green
        "Glass": "#F59E0B",         # Amber
        "Paper": "#EAB308",         # Yellow
        "Hazardous Waste": "#EF4444",
        "Textile Waste": "#EC4899",
        "Mixed Waste": "#64748B",
        "Other Waste": "#94A3B8"
    }

    cat = analysis["predicted_category"]
    color = category_colors.get(cat, "#8B5CF6" if "E-Waste" in cat else "#3B82F6")

    bbox = analysis.get("bounding_box", [0.1, 0.1, 0.9, 0.9])
    ymin, xmin, ymax, xmax = bbox
    bbox_xywh = analysis.get("bbox_xywh", [xmin, ymin, round(xmax - xmin, 4), round(ymax - ymin, 4)])

    # Model name & metrics
    m_name = active_model.model_name if active_model else "Waste Detection Model v2.1"
    m_ver = active_model.version if active_model else "v2.1"
    m_framework = active_model.framework if active_model else "PyTorch 2.2 / YOLOv8-Waste"
    m_acc = active_model.accuracy if active_model else 0.918

    return {
        "success": True,
        "model": {
            "name": m_name,
            "version": m_ver,
            "framework": m_framework,
            "accuracy": m_acc,
            "status": "Active"
        },
        "predictions": [
            {
                "object_name": analysis["detected_item"],
                "waste_category": cat,
                "confidence": analysis["confidence_pct"],
                "confidence_raw": analysis["confidence"],
                "bbox": analysis["bounding_box"],
                "bbox_xywh": bbox_xywh,
                "color": color
            }
        ],
        "bounding_box": analysis["bounding_box"],
        "bbox_xywh": bbox_xywh,
        "detected_item": analysis["detected_item"],
        "waste_category": cat,
        "confidence_pct": analysis["confidence_pct"],
        "color": color,
        "embedding": analysis.get("embedding", []),
        "classification_method": analysis.get("classification_method", "primary_ai"),
        "fallback_used": analysis.get("fallback_used", False),
        "requires_review": analysis.get("requires_review", False),
        "fallback_details": analysis.get("fallback_details")
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    from app.core.database import check_database_health
    db_health = check_database_health()
    active_model = db.query(AIModelVersion).filter(AIModelVersion.is_active_production == True).first()
    return {
        "status": "healthy" if db_health.get("healthy") else "degraded",
        "service": settings.PROJECT_NAME,
        "city": "Chennai, Tamil Nadu",
        "database": db_health,
        "active_model": {
            "version": active_model.version if active_model else "v2.1",
            "name": active_model.model_name if active_model else "GCC-WasteVision",
            "status": "Production"
        },
        "storage": {
            "provider": settings.STORAGE_PROVIDER,
            "bucket": settings.STORAGE_BUCKET if settings.STORAGE_PROVIDER == "s3" else "local_disk"
        },
        "zones_count": 15,
        "wards_count": 200,
        "version": "2.2.0"
    }

# Safe global error handler avoiding information leakage
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "user_message": "An unexpected error occurred while processing the municipal request. Please try again or contact support."
        }
    )
