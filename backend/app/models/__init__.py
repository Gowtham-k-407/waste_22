from app.models.user import User, PasswordResetToken
from app.models.memory import UserAIRef
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
from app.models.iot import IoTDevice, DeviceTelemetry

__all__ = [
    "User",
    "PasswordResetToken",
    "UserAIRef",
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
    "DeviceTelemetry"
]