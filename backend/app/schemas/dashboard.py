from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DataProvenance(BaseModel):
    source: str
    dataset_name: str
    last_updated: str
    data_type: str # LIVE DATA, NEAR REAL-TIME DATA, HISTORICAL DATA, USER-CONTRIBUTED DATA, AI-DETECTED DATA, SIMULATED DATA
    reliability: str = "High"
    notes: Optional[str] = None

class MetricCard(BaseModel):
    title: str
    value: str
    numeric_value: float
    unit: str
    trend: str
    trend_direction: str # up, down, neutral
    trend_is_good: bool
    provenance: DataProvenance
    explanation: str

class CategoryItem(BaseModel):
    id: int
    name: str
    quantity_tons: float
    percentage: float
    color: str
    recyclability_pct: float
    trend: str

class DashboardSummary(BaseModel):
    total_waste_today_tons: MetricCard
    total_waste_week_tons: MetricCard
    total_waste_month_tons: MetricCard
    recycling_rate: MetricCard
    segregation_efficiency: MetricCard
    estimated_environmental_co2e: MetricCard
    active_vehicles_count: MetricCard
    active_plants_count: MetricCard
    total_processing_capacity_tpd: MetricCard
    plant_capacity_utilization_pct: MetricCard
    categories: List[CategoryItem]
    top_waste_category: str
    simulation_mode: bool
