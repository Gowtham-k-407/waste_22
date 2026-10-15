from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import UserBase

class UserAIRef(UserBase):
    __tablename__ = "user_ai_references"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    image_id = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    image_hash = Column(String, index=True, nullable=False)
    confirmed_item = Column(String, nullable=False) # e.g. "Mobile Phone", "Laptop", "Battery"
    confirmed_waste_category = Column(String, default="E-Waste", nullable=False) # e.g. "E-Waste"
    image_embedding_json = Column(Text, nullable=False) # 128-dimensional dense float vector in JSON
    embedding_model_version = Column(String, default="v2.2-embed")
    reference_status = Column(String, default="active") # "active", "archived"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)