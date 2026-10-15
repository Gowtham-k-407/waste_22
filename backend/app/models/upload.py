import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from app.core.database import Base

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, unique=True, index=True, default=lambda: f"UPL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    user_id = Column(Integer, nullable=True, index=True) # Linked to User in Database A
    user_name = Column(String, default="Citizen Contributor")
    user_email = Column(String, nullable=True)

    original_filename = Column(String, nullable=False)
    stored_image_path = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String, default="image/jpeg")
    content_hash = Column(String, nullable=True, index=True)

    # User-provided metadata
    category = Column(String, default="Unknown") # User category selection
    object_label = Column(String, nullable=False) # e.g. Mobile Phone, Plastic Bottle
    description = Column(Text, nullable=True)
    location_context = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Initial status: PENDING_VERIFICATION
    # Values: PENDING_VERIFICATION, Approved, Rejected, Added to Dataset, Used for Training
    status = Column(String, default="PENDING_VERIFICATION", index=True)

    # Automated AI pre-classification hints
    ai_predicted_category = Column(String, nullable=True)
    ai_predicted_label = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)

    # Admin verification fields
    verified_by_admin_id = Column(Integer, nullable=True)
    verified_by_admin_name = Column(String, nullable=True)
    verified_category = Column(String, nullable=True) # If admin corrects label/category
    verified_label = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Provenance tracking
    source_provenance = Column(String, default="Citizen WebCam Contribution")
    license = Column(String, default="Creative Commons CC-BY 4.0")

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    verified_at = Column(DateTime, nullable=True)


class DatasetImage(Base):
    __tablename__ = "dataset_images"

    id = Column(Integer, primary_key=True, index=True)
    dataset_code = Column(String, unique=True, index=True, default=lambda: f"DS-IMG-{uuid.uuid4().hex[:8].upper()}")
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True, index=True)

    image_url = Column(String, nullable=False)
    stored_image_path = Column(String, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    
    # Standard Categories: Plastic, Paper, Metal, Glass, Organic Waste, E-Waste, Cardboard, Food Waste, Textile Waste, Hazardous Waste, Mixed Waste
    waste_category = Column(String, index=True, nullable=False)
    object_label = Column(String, nullable=False) # e.g. Smartphone, Li-ion Battery, PET Bottle
    description = Column(Text, nullable=True)
    location_context = Column(String, nullable=True)

    split = Column(String, default="train") # train (70%), val (15%), test (15%)
    verified_by = Column(String, default="System Administrator")
    verified_at = Column(DateTime, default=datetime.utcnow)
    used_in_training = Column(Boolean, default=False, index=True)
    
    source_provenance = Column(String, default="Verified Municipal Dataset Hub")
    license = Column(String, default="Open Data License (ODbL) / CC-BY 4.0")
    created_at = Column(DateTime, default=datetime.utcnow)
