import os
from typing import List, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

def normalize_database_url(url: str) -> str:
    """Ensure database URL is SQLAlchemy-compatible (fix Heroku/Render postgres:// prefix)."""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

class Settings(BaseModel):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Chennai Solid Waste Segregation & AI Optimization Platform")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api")

    # Security & Auth
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "chennai-smart-waste-municipal-secret-key-2026"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))) # 7 days

    # CORS
    CORS_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,https://waste-22.onrender.com"
        ).split(",") if origin.strip()
    ]

    # Base Directories
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads"))
    MODELS_DIR: str = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models_checkpoints"))

    # Three Distinct Logical Databases (Database A: User, Database B: Staff, Database C: Waste)
    USER_DATABASE_URL: str = normalize_database_url(
        os.getenv(
            "USER_DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'users.db').replace(os.sep, '/')}"
        )
    )
    STAFF_DATABASE_URL: str = normalize_database_url(
        os.getenv(
            "STAFF_DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'staff.db').replace(os.sep, '/')}"
        )
    )
    WASTE_DATABASE_URL: str = normalize_database_url(
        os.getenv(
            "WASTE_DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'waste_management.db').replace(os.sep, '/')}"
        )
    )
    # Legacy fallback database pointer
    DATABASE_URL: str = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'chennai_waste.db').replace(os.sep, '/')}"
        )
    )

    # Storage Configuration (Local or S3-compatible: AWS S3, Cloudflare R2, MinIO)
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local").lower() # "local" | "s3"
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "wastedash-assets")
    STORAGE_ENDPOINT: str = os.getenv("STORAGE_ENDPOINT", "")
    STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY", "")
    STORAGE_REGION: str = os.getenv("STORAGE_REGION", "ap-south-1") # Chennai / Mumbai region

    # Standalone AI Microservice Configuration (Independently Deployed)
    AI_SERVICE_BASE_URL: str = os.getenv("AI_SERVICE_BASE_URL", os.getenv("AI_INFERENCE_URL", "http://localhost:8001"))
    AI_SERVICE_API_KEY: str = os.getenv("AI_SERVICE_API_KEY", os.getenv("AI_INFERENCE_API_KEY", ""))
    AI_INFERENCE_URL: str = os.getenv("AI_INFERENCE_URL", os.getenv("AI_SERVICE_BASE_URL", "http://localhost:8001"))
    AI_INFERENCE_API_KEY: str = os.getenv("AI_INFERENCE_API_KEY", os.getenv("AI_SERVICE_API_KEY", ""))


    # AI Fallback & Classification Configuration
    FALLBACK_CLASSIFICATION_ENABLED: bool = os.getenv("FALLBACK_CLASSIFICATION_ENABLED", "true").lower() in ("true", "1", "yes")
    AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.45"))
    FRAME_SAMPLING_INTERVAL_MS: int = int(os.getenv("FRAME_SAMPLING_INTERVAL_MS", "300"))
    MAX_IMAGE_SIZE_MB: float = float(os.getenv("MAX_IMAGE_SIZE_MB", "15.0"))
    INFERENCE_TIMEOUT_SECONDS: float = float(os.getenv("INFERENCE_TIMEOUT_SECONDS", os.getenv("AI_INFERENCE_TIMEOUT_SECONDS", "15.0")))

    # Adafruit IO MQTT Configuration
    ADAFRUIT_IO_USERNAME: str = os.getenv("ADAFRUIT_IO_USERNAME", "")
    ADAFRUIT_IO_KEY: str = os.getenv("ADAFRUIT_IO_KEY", "")
    ADAFRUIT_IO_HOST: str = os.getenv("ADAFRUIT_IO_HOST", "io.adafruit.com")
    ADAFRUIT_IO_PORT: int = int(os.getenv("ADAFRUIT_IO_PORT", "8883"))
    ADAFRUIT_IO_USE_TLS: bool = os.getenv("ADAFRUIT_IO_USE_TLS", "true").lower() in ("true", "1", "yes")
    ADAFRUIT_IO_FEED_PREFIX: str = os.getenv("ADAFRUIT_IO_FEED_PREFIX", "wastedash")
    ADAFRUIT_IO_FEEDS: List[str] = [
        f.strip() for f in os.getenv(
            "ADAFRUIT_IO_FEEDS",
            "wastedash-telemetry,wastedash-bin-fill,wastedash-scale-weight,wastedash-temperature,wastedash-humidity,wastedash-device-status"
        ).split(",") if f.strip()
    ]
    # Legacy broker aliases for backward compatibility
    MQTT_BROKER_URL: str = os.getenv("MQTT_BROKER_URL", os.getenv("ADAFRUIT_IO_HOST", "io.adafruit.com"))
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", str(os.getenv("ADAFRUIT_IO_PORT", "8883"))))
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", os.getenv("ADAFRUIT_IO_USERNAME", ""))
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", os.getenv("ADAFRUIT_IO_KEY", ""))
    MQTT_TLS_ENABLED: bool = os.getenv("MQTT_TLS_ENABLED", "true").lower() in ("true", "1", "yes")
    MQTT_TOPIC_PREFIX: str = os.getenv("MQTT_TOPIC_PREFIX", "wastedash")

    # System & Simulation Flags
    TRAINING_THRESHOLD: int = int(os.getenv("TRAINING_THRESHOLD", "500"))
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", os.getenv("SIMULATION_MODE_DEFAULT", "true")).lower() in ("true", "1", "yes")
    SIMULATION_TICK_SECONDS: int = int(os.getenv("SIMULATION_TICK_SECONDS", "8"))

    # Administrator Bootstrap Credentials (Initial Setup Only)
    ADMIN_BOOTSTRAP_EMAIL: str = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "admin@wastesegeregate.in")
    ADMIN_BOOTSTRAP_PASSWORD: str = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "admin123")

settings = Settings()
