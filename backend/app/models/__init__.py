# Database A: User & Auth Models
from app.models.user import User, PasswordResetToken, AuthAuditLog
from app.models.memory import UserAIRef

# Database B: Municipal Staff Models
from app.models.staff import StaffProfile, StaffDutyAssignment, StaffAuditLog

# Database C: Waste Operations & AI Operations Models
from app.models.geography import Zone, Ward
from app.models.waste import WasteCategory, WasteRecord
from app.models.facility import SegregationPlant
from app.models.vehicle import CollectionVehicle
from app.models.detection import AIDetection
from app.models.contribution import ImageContribution
from app.models.upload import Upload, DatasetImage
from app.models.ai_model import AIModelVersion, TrainingJob
from app.models.dataset import DatasetSource, DatasetImport
from app.models.optimization import EnvironmentalMetric, OperationalAlert, OptimizationRecommendation
from app.models.iot import IoTDevice, DeviceTelemetry, IoTSortingRecord
from app.models.complaint import (
    PublicComplaint, ComplaintFollowUp, Notification,
    WeighbridgeRecord, SimulationRun, AIInferenceAudit
)

__all__ = [
    # Database A
    "User",
    "PasswordResetToken",
    "AuthAuditLog",
    "UserAIRef",
    # Database B
    "StaffProfile",
    "StaffDutyAssignment",
    "StaffAuditLog",
    # Database C
    "Zone",
    "Ward",
    "WasteCategory",
    "WasteRecord",
    "SegregationPlant",
    "CollectionVehicle",
    "AIDetection",
    "ImageContribution",
    "Upload",
    "DatasetImage",
    "AIModelVersion",
    "TrainingJob",
    "DatasetSource",
    "DatasetImport",
    "EnvironmentalMetric",
    "OperationalAlert",
    "OptimizationRecommendation",
    "IoTDevice",
    "DeviceTelemetry",
    "IoTSortingRecord",
    "PublicComplaint",
    "ComplaintFollowUp",
    "Notification",
    "WeighbridgeRecord",
    "SimulationRun",
    "AIInferenceAudit"
]