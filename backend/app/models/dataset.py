from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.core.database import Base

class DatasetSource(Base):
    __tablename__ = "dataset_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    provider = Column(String, nullable=False) # Greater Chennai Corporation, CPCB, TNPCB, Kaggle Solid Waste, Smart Truck IoT Stream
    dataset_type = Column(String, default="HISTORICAL DATA") # LIVE, NEAR REAL-TIME, HISTORICAL, USER-CONTRIBUTED, AI-DETECTED, SIMULATED
    update_frequency = Column(String, default="Daily")
    reliability_status = Column(String, default="Verified Official Portal")
    row_count = Column(Integer, default=54000)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    endpoint_or_file = Column(String)
    description = Column(Text)
    license = Column(String, default="Open Government Data (OGD) India / Creative Commons")

class DatasetImport(Base):
    __tablename__ = "dataset_imports"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer)
    filename = Column(String, nullable=False)
    record_count = Column(Integer, default=0)
    imported_by = Column(String, default="System Admin")
    status = Column(String, default="Completed") # Validated, Completed, Failed
    imported_at = Column(DateTime, default=datetime.utcnow)
    mapping_details = Column(Text)
