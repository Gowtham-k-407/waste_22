import os
from typing import List, Union
from pydantic import BaseModel, Field

def normalize_database_url(url: str) -> str:
    """Ensure database URL is SQLAlchemy-compatible (fix Heroku/Render postgres:// prefix)."""
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

    # Database
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
    
    # AI Inference Microservice (Optional Decoupled Service)
    AI_INFERENCE_URL: str = os.getenv("AI_INFERENCE_URL", "")
    AI_INFERENCE_API_KEY: str = os.getenv("AI_INFERENCE_API_KEY", "")
    
    # MQTT IoT Configuration
    MQTT_BROKER_URL: str = os.getenv("MQTT_BROKER_URL", "")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")
    MQTT_TLS_ENABLED: bool = os.getenv("MQTT_TLS_ENABLED", "false").lower() in ("true", "1", "yes")
    MQTT_TOPIC_PREFIX: str = os.getenv("MQTT_TOPIC_PREFIX", "wastedash")
    
    # System Flags
    TRAINING_THRESHOLD: int = int(os.getenv("TRAINING_THRESHOLD", "500"))
    SIMULATION_MODE_DEFAULT: bool = os.getenv("SIMULATION_MODE_DEFAULT", "false").lower() in ("true", "1", "yes")

settings = Settings()
