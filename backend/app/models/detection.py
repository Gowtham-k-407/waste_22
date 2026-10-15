from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.core.database import Base

class AIDetection(Base):
    __tablename__ = "ai_detections"
    id = Column(Integer, primary_key=True, index=True)
    detection_code = Column(String, unique=True, index=True)
    vehicle_code = Column(String, index=True)
    ward_number = Column(Integer, index=True)
    location_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    waste_category = Column(String, nullable=False) # e.g. Plastic Bottle, Cardboard Box, Organic Food
    confidence = Column(Float, nullable=False) # e.g. 0.94
    bounding_box_json = Column(Text) # JSON of bbox [ymin, xmin, ymax, xmax]
    image_url = Column(String)
    model_version = Column(String, default="v2.1")
    estimated_weight_kg = Column(Float, default=1.2)
    bin_fill_level_pct = Column(Float, default=65.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    data_type = Column(String, default="AI-DETECTED DATA")
