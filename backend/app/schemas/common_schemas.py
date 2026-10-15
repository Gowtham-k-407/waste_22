from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WasteCategorySchema(BaseModel):
    id: int
    name: str
    color: str
    recyclability_pct: float
    description: Optional[str]
    handling_instructions: Optional[str]
    class Config:
        from_attributes = True

class PlantSchema(BaseModel):
    id: int
    name: str
    facility_type: str
    latitude: float
    longitude: float
    capacity_tpd: float
    current_input_tpd: float
    utilization_pct: float
    status: str
    accepted_categories: str
    operator_name: str
    contact_phone: str
    address: Optional[str]
    class Config:
        from_attributes = True

class VehicleSchema(BaseModel):
    id: int
    vehicle_code: str
    vehicle_type: str
    registration_no: str
    driver_name: str
    driver_phone: str
    capacity_tons: float
    current_fill_pct: float
    battery_or_fuel_pct: float
    status: str
    latitude: float
    longitude: float
    assigned_zone_id: int
    assigned_ward_id: int
    assigned_route: str
    current_speed_kmh: float
    last_ping: datetime
    camera_status: str
    class Config:
        from_attributes = True

class AIDetectionSchema(BaseModel):
    id: int
    detection_code: str
    vehicle_code: str
    ward_number: int
    location_name: Optional[str]
    latitude: float
    longitude: float
    waste_category: str
    confidence: float
    bounding_box: Optional[List[float]] = None
    image_url: Optional[str]
    model_version: str
    estimated_weight_kg: float
    bin_fill_level_pct: float
    timestamp: datetime
    data_type: str
    class Config:
        from_attributes = True

class ContributionSchema(BaseModel):
    id: int
    contributor_name: str
    image_url: str
    file_size_kb: float
    ai_predicted_category: str
    ai_confidence: float
    user_confirmed_category: str
    is_user_corrected: bool
    user_notes: Optional[str]
    blur_score: float
    quality_status: str
    validation_status: str
    rejection_reason: Optional[str]
    ward_number: Optional[int]
    location_name: Optional[str]
    created_at: datetime
    data_type: str
    class Config:
        from_attributes = True

class AIModelSchema(BaseModel):
    id: int
    model_name: str
    version: str
    status: str
    framework: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_images_count: int
    training_date: datetime
    dataset_version: str
    notes: Optional[str]
    is_active_production: bool
    class Config:
        from_attributes = True

class AlertSchema(BaseModel):
    id: int
    alert_code: str
    priority: str
    category: str
    location_name: str
    ward_number: Optional[int]
    issue: str
    recommended_action: str
    status: str
    timestamp: datetime
    class Config:
        from_attributes = True

class OptimizationSchema(BaseModel):
    id: int
    recommendation_code: str
    category: str
    ward_number: Optional[int]
    ward_name: Optional[str]
    target_plant_name: Optional[str]
    title: str
    description: str
    expected_benefit: str
    confidence_score: float
    status: str
    created_at: datetime
    tag: str
    class Config:
        from_attributes = True
