from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from app.core.database import Base

class SegregationPlant(Base):
    __tablename__ = "segregation_plants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # e.g. Perungudi Waste Processing Center, Kodungaiyur MRF, Madhavaram Bio-CNG Plant
    facility_type = Column(String, nullable=False) # Segregation Plant, Recycling Facility, Composting Plant, Bio-CNG, Transfer Station, Landfill
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_tpd = Column(Float, nullable=False) # Tons Per Day
    current_input_tpd = Column(Float, default=0.0)
    status = Column(String, default="active") # active, inactive, maintenance, unknown
    accepted_categories = Column(String, default="Organic,Plastic,Paper,Metal,Glass")
    operator_name = Column(String, default="Urbaser Sumeet / GCC")
    contact_phone = Column(String, default="+91 44 2538 4520")
    address = Column(Text)
