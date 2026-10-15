from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from app.core.database import Base

class EnvironmentalMetric(Base):
    __tablename__ = "environmental_metrics"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, index=True, nullable=True)
    ward_number = Column(Integer, index=True, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    co2e_avoided_tons = Column(Float, default=145.8)
    methane_emission_risk_tons = Column(Float, default=42.3)
    plastic_leak_risk_score = Column(Float, default=38.0) # 0 to 100
    landfill_burden_saved_m3 = Column(Float, default=210.5)
    recyclable_loss_tons = Column(Float, default=18.2)
    calculation_methodology = Column(String, default="CPCB SWM 2016 & IPCC Waste Model Tier-1 Estimation")
    disclaimer = Column(Text, default="These are estimated environmental indicators based on available waste data and defined calculation methodologies. Not official pollution measurements.")

class OperationalAlert(Base):
    __tablename__ = "operational_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String, unique=True, index=True)
    priority = Column(String, default="High") # Critical, High, Medium, Low
    category = Column(String, default="Segregation") # Accumulation, Segregation, Plant Capacity, AI Confidence, Collection Route
    location_name = Column(String, nullable=False) # e.g. Ward 82 (Anna Nagar West), Perungudi Plant
    ward_number = Column(Integer, nullable=True)
    issue = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    status = Column(String, default="Active") # Active, In Progress, Resolved, Dismissed
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    recommendation_code = Column(String, unique=True, index=True)
    category = Column(String, default="Collection Frequency") # Collection Frequency, Route Rerouting, Plant Load Balancing, Resource Allocation
    ward_number = Column(Integer, nullable=True)
    ward_name = Column(String, nullable=True)
    target_plant_name = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    expected_benefit = Column(String, nullable=False) # e.g. "+14% Segregation efficiency", "Saves 42km fleet travel"
    confidence_score = Column(Float, default=0.91)
    status = Column(String, default="Active") # Active, Implemented, In Review
    created_at = Column(DateTime, default=datetime.utcnow)
    tag = Column(String, default="AI RECOMMENDATION")
