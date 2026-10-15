from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.core.database import Base

class CollectionVehicle(Base):
    __tablename__ = "collection_vehicles"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_code = Column(String, unique=True, index=True, nullable=False) # e.g. GC-01 to GC-24
    vehicle_type = Column(String, default="Smart Compactor Truck")
    registration_no = Column(String, nullable=False)
    driver_name = Column(String, nullable=False)
    driver_phone = Column(String, default="+91 98400 12345")
    capacity_tons = Column(Float, default=5.0)
    current_fill_pct = Column(Float, default=45.0)
    battery_or_fuel_pct = Column(Float, default=85.0)
    status = Column(String, default="collecting") # collecting, in_transit, unloading, maintenance, idle
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    assigned_zone_id = Column(Integer, default=5)
    assigned_ward_id = Column(Integer, default=102)
    assigned_route = Column(String, default="Royapuram - George Town Sector B")
    current_speed_kmh = Column(Float, default=18.5)
    last_ping = Column(DateTime, default=datetime.utcnow)
    camera_status = Column(String, default="Active - Streaming AI Feed")
