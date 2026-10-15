import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import synonym
from app.core.database import WasteBase

class PublicComplaint(WasteBase):
    __tablename__ = "public_complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_code = Column(String, unique=True, index=True, default=lambda: f"GCC-SAN-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}")
    
    # Category: Missed garbage collection, Overflowing bins, Illegal dumping, Drainage leakage, Drainage blockage, Street cleaning, Damaged bins, Other sanitation problems
    category = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Location
    location_name = Column(String, nullable=False)
    ward_number = Column(Integer, nullable=False, index=True)
    zone_number = Column(Integer, nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Submitter info (Service-layer link to Database A user)
    citizen_user_id = Column(Integer, nullable=True, index=True)
    citizen_name = Column(String, default="Resident of Chennai")
    citizen_phone = Column(String, nullable=True)
    citizen_email = Column(String, nullable=True)
    
    # Priority & Evidence
    priority = Column(String, default="Medium", index=True) # Critical, High, Medium, Low
    evidence_image_url = Column(String, nullable=True)
    
    # Assignment (Service-layer link to Database B staff)
    assigned_department = Column(String, default="Solid Waste Management", index=True)
    assigned_staff_id = Column(Integer, nullable=True, index=True)
    assigned_staff_name = Column(String, nullable=True)
    assigned_staff_phone = Column(String, nullable=True)
    
    # Status Workflow: Submitted -> Assigned -> In Progress -> Resolved -> Closed (or Reopened)
    status = Column(String, default="Submitted", index=True)
    status_history_json = Column(Text, default="[]") # List of {status, timestamp, updated_by, notes}
    
    # Resolution details
    resolution_notes = Column(Text, nullable=True)
    resolution_evidence_url = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Flag indicating synthetic provenance for demonstrations
    is_simulated = Column(Boolean, default=False, index=True)
    data_source = Column(String, default="citizen_portal") # citizen_portal, simulation, control_room
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Synonyms for seamless API & ORM backwards/forwards compatibility
    tracking_number = synonym("complaint_code")
    ward_id = synonym("ward_number")
    reporter_user_id = synonym("citizen_user_id")
    location_address = synonym("location_name")
    photo_evidence_url = synonym("evidence_image_url")
    reporter_name = synonym("citizen_name")
    reporter_phone = synonym("citizen_phone")
    reporter_email = synonym("citizen_email")

    @property
    def title(self) -> str:
        cat_title = (self.category or "Grievance").replace("_", " ").title()
        loc = f" at {self.location_name}" if self.location_name else ""
        return f"{cat_title}{loc}"

    @property
    def current_escalation_tier(self) -> int:
        if not self.status_history_json:
            return 0
        try:
            import json
            history = json.loads(self.status_history_json)
            tiers = [entry.get("escalation_tier", 0) for entry in history if isinstance(entry, dict) and "escalation_tier" in entry]
            return max(tiers) if tiers else 0
        except Exception:
            return 0

    @property
    def sla_hours(self) -> int:
        return 24 if (self.priority or "").lower() in ("critical", "high") else 48

    @property
    def is_escalation_eligible(self) -> bool:
        if (self.status or "").lower() in ("resolved", "closed"):
            return False
        if self.current_escalation_tier >= 3:
            return False
        return True


GCC_ESCALATION_HIERARCHY = [
    {"tier": 0, "title": "Ward Sanitary Inspector", "department": "Ward Sanitation Office"},
    {"tier": 1, "title": "Assistant Engineer / Zonal Sanitation Officer", "department": "Zonal Health & Sanitation Wing"},
    {"tier": 2, "title": "Municipal Health Officer", "department": "GCC Public Health Directorate"},
    {"tier": 3, "title": "Municipal Commissioner Executive Cell", "department": "Commissioner Executive Grievance Cell"}
]


class ComplaintFollowUp(WasteBase):
    __tablename__ = "complaint_follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("public_complaints.id"), index=True, nullable=False)
    author_type = Column(String, default="citizen") # citizen, staff, system, citizen_escalation
    author_name = Column(String, nullable=False)
    author_user_id = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    evidence_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Synonyms
    author_role = synonym("author_type")
    attachment_url = synonym("evidence_url")


class Notification(WasteBase):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, index=True, nullable=True) # Specific user or null for broadcast
    recipient_role = Column(String, index=True, nullable=True) # Target role code
    target_ward_number = Column(Integer, nullable=True, index=True) # Ward-targeted notifications
    target_department = Column(String, nullable=True, index=True) # Department-targeted
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String, default="Operational") # Operational, Grievance, Alert, System, AI
    priority = Column(String, default="Normal") # Urgent, High, Normal, Info
    link_url = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class WeighbridgeRecord(WasteBase):
    __tablename__ = "weighbridge_records"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True, default=lambda: f"WB-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}")
    facility_id = Column(Integer, ForeignKey("segregation_plants.id"), nullable=False, index=True)
    facility_name = Column(String, nullable=False)
    vehicle_code = Column(String, nullable=False, index=True)
    gross_weight_tons = Column(Float, nullable=False)
    tare_weight_tons = Column(Float, nullable=False)
    net_weight_tons = Column(Float, nullable=False)
    primary_waste_category = Column(String, default="Mixed Waste")
    operator_staff_id = Column(Integer, nullable=True)
    operator_name = Column(String, default="Weighbridge Operator")
    source_ward_number = Column(Integer, nullable=True)
    is_simulated = Column(Boolean, default=False, index=True)
    data_source = Column(String, default="weighbridge_terminal")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class SimulationRun(WasteBase):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    simulation_run_id = Column(String, unique=True, index=True)
    status = Column(String, default="running") # running, paused, stopped
    tick_interval_seconds = Column(Integer, default=8)
    events_generated = Column(Integer, default=0)
    last_tick_at = Column(DateTime, default=datetime.utcnow)
    active_vehicles_count = Column(Integer, default=24)
    active_bins_count = Column(Integer, default=120)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIInferenceAudit(WasteBase):
    __tablename__ = "ai_inference_audit"

    id = Column(Integer, primary_key=True, index=True)
    image_hash = Column(String, index=True, nullable=True)
    filename = Column(String, nullable=True)
    classification_method = Column(String, nullable=False, index=True) # neural_yolo, neural_mobilenet, fallback_heuristic, fallback_cv
    primary_model_status = Column(String, default="active") # success, failed, timeout, low_confidence, unavailable
    fallback_used = Column(Boolean, default=False, index=True)
    predicted_category = Column(String, nullable=False, index=True)
    detected_item = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    heuristic_score = Column(Float, nullable=True)
    requires_review = Column(Boolean, default=False, index=True)
    processing_time_ms = Column(Float, default=0.0)
    is_simulated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
