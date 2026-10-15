from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class WardSummary(BaseModel):
    id: int
    ward_number: int
    name: str
    zone_number: int
    zone_name: str
    latitude: float
    longitude: float
    population: int
    daily_waste_tons: float
    segregation_efficiency: float
    pollution_risk_score: float
    recycling_potential: float
    primary_waste_type: str
    collection_frequency_per_day: int
    class Config:
        from_attributes = True

class WardDetail(WardSummary):
    category_breakdown: List[Dict[str, Any]]
    nearby_plants: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    ai_recommendations: List[str]

class WardRanking(BaseModel):
    ranking_type: str
    title: str
    description: str
    wards: List[Dict[str, Any]]
