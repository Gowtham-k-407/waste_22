from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class WasteCategory(Base):
    __tablename__ = "waste_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # e.g. Organic, Food Waste, Plastic, Paper, Cardboard, Glass, Metal, Textile, E-Waste, Hazardous, Mixed
    color = Column(String, default="#10B981")
    recyclability_pct = Column(Float, default=80.0)
    description = Column(Text)
    handling_instructions = Column(Text)

class WasteRecord(Base):
    __tablename__ = "waste_records"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), index=True)
    category_id = Column(Integer, ForeignKey("waste_categories.id"), index=True)
    quantity_kg = Column(Float, nullable=False)
    segregation_status = Column(String, default="Segregated") # Segregated, Partially Segregated, Mixed
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    data_source = Column(String, default="Greater Chennai Corporation")
    data_type = Column(String, default="HISTORICAL DATA") # LIVE DATA, NEAR REAL-TIME DATA, HISTORICAL DATA, USER-CONTRIBUTED DATA, AI-DETECTED DATA, SIMULATED DATA
    collection_vehicle_id = Column(Integer, nullable=True)
    plant_id = Column(Integer, nullable=True)
