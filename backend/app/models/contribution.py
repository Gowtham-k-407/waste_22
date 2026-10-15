from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from datetime import datetime
from app.core.database import Base

class ImageContribution(Base):
    __tablename__ = "image_contributions"
    id = Column(Integer, primary_key=True, index=True)
    contributor_name = Column(String, default="Citizen Volunteer")
    contributor_email = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    image_hash = Column(String, index=True)
    file_size_kb = Column(Float, default=120.0)
    ai_predicted_category = Column(String, nullable=False)
    ai_confidence = Column(Float, nullable=False)
    user_confirmed_category = Column(String, nullable=False)
    is_user_corrected = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    
    # Image Quality Validation Pipeline
    blur_score = Column(Float, default=85.0) # Laplacian variance
    quality_status = Column(String, default="valid") # valid, blurry, low_resolution, duplicate, invalid
    validation_status = Column(String, default="staged_for_training") # pending, staged_for_training, approved_in_dataset, rejected
    rejection_reason = Column(String, nullable=True)
    
    ward_number = Column(Integer, nullable=True)
    location_name = Column(String, default="Chennai Municipal Area")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    data_type = Column(String, default="USER-CONTRIBUTED DATA")
