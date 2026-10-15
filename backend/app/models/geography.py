from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    zone_number = Column(Integer, unique=True, index=True)
    name = Column(String, nullable=False)
    headquarters = Column(String)
    wards = relationship("Ward", back_populates="zone")

class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True, index=True)
    ward_number = Column(Integer, unique=True, index=True)
    name = Column(String, nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    population = Column(Integer, default=45000)
    area_sqkm = Column(Float, default=2.5)
    daily_waste_tons = Column(Float, default=28.5)
    segregation_efficiency = Column(Float, default=62.5) # Percentage
    pollution_risk_score = Column(Float, default=45.0) # 0 to 100
    recycling_potential = Column(Float, default=74.0)
    primary_waste_type = Column(String, default="Organic Waste")
    collection_frequency_per_day = Column(Integer, default=2)

    zone = relationship("Zone", back_populates="wards")
