import io
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings

logger = logging.getLogger("wastedash.ai_client")


class AIServiceUnavailableException(Exception):
    """Raised when standalone AI service is unreachable or returns a 5xx error."""
    pass


class AIServiceResponseException(Exception):
    """Raised when standalone AI service returns a 4xx validation or processing error."""
    pass


class AIServiceClient:
    """
    Dedicated HTTP Client for communicating with the standalone, independently deployed
    WasteDash AI Microservice.

    Features:
      - Connection pooling via requests.Session.
      - Configurable base URL: settings.AI_SERVICE_BASE_URL.
      - Connection and read timeouts.
      - Bounded idempotency-safe retries (GET/HEAD only).
      - Strict response validation.
      - No sensitive data/image logging.
    """
    _session: Optional[requests.Session] = None

    @classmethod
    def get_session(cls) -> requests.Session:
        if cls._session is None:
            s = requests.Session()
            # Bounded retry strategy only for safe idempotent methods (GET, HEAD, OPTIONS)
            retries = Retry(
                total=2,
                backoff_factor=0.3,
                status_forcelist=[502, 503, 504],
                allowed_methods=["GET", "HEAD", "OPTIONS"]
            )
            adapter = HTTPAdapter(
                pool_connections=10,
                pool_maxsize=25,
                max_retries=retries
            )
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            cls._session = s
        return cls._session

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        headers = {}
        api_key = settings.AI_SERVICE_API_KEY
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key
        return headers

    @classmethod
    def get_base_url(cls) -> str:
        return (settings.AI_SERVICE_BASE_URL or "http://localhost:8001").rstrip("/")

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """
        Check health and readiness of standalone AI Microservice.
        GET /health or /api/v1/ai/health
        """
        base = cls.get_base_url()
        timeout = settings.INFERENCE_TIMEOUT_SECONDS
        session = cls.get_session()
        try:
            resp = session.get(f"{base}/health", headers=cls.get_headers(), timeout=min(5.0, timeout))
            if resp.status_code == 200:
                return resp.json()
            # Fallback check
            resp = session.get(f"{base}/api/v1/ai/health", headers=cls.get_headers(), timeout=min(5.0, timeout))
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service health check returned HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            logger.warning(f"AI Service health check failed: {e}")
            raise AIServiceUnavailableException(f"Standalone AI microservice unreachable at {base}") from e

    @classmethod
    def classify_image(
        cls,
        image: Image.Image,
        upload_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit still image for ResNet50 classification.
        POST /api/v1/ai/predict/image
        """
        base = cls.get_base_url()
        timeout = settings.INFERENCE_TIMEOUT_SECONDS
        session = cls.get_session()

        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=90)
        img_bytes = buf.getvalue()

        try:
            resp = session.post(
                f"{base}/api/v1/ai/predict/image",
                files={"file": (f"upload_{upload_id or 'img'}.jpg", img_bytes, "image/jpeg")},
                headers=cls.get_headers(),
                timeout=timeout
            )
            if resp.status_code == 200:
                return resp.json()
            elif 400 <= resp.status_code < 500:
                raise AIServiceResponseException(f"AI Service rejected image: HTTP {resp.status_code} - {resp.text}")
            else:
                raise AIServiceUnavailableException(f"AI Service error: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            logger.error(f"AI Service classification request failed: {e}")
            raise AIServiceUnavailableException(f"AI Service connection failed: {e}") from e

    @classmethod
    def detect_frame(
        cls,
        image: Image.Image,
        frame_id: Optional[str] = None,
        conf_threshold: float = 0.25
    ) -> Dict[str, Any]:
        """
        Submit camera / video frame for YOLO11n object detection.
        POST /api/v1/ai/predict/frame
        """
        base = cls.get_base_url()
        timeout = settings.INFERENCE_TIMEOUT_SECONDS
        session = cls.get_session()

        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=85)
        img_bytes = buf.getvalue()

        try:
            resp = session.post(
                f"{base}/api/v1/ai/predict/frame?conf_threshold={conf_threshold}",
                files={"file": (f"frame_{frame_id or 'cam'}.jpg", img_bytes, "image/jpeg")},
                headers=cls.get_headers(),
                timeout=timeout
            )
            if resp.status_code == 200:
                return resp.json()
            elif 400 <= resp.status_code < 500:
                raise AIServiceResponseException(f"AI Service rejected frame: HTTP {resp.status_code} - {resp.text}")
            else:
                raise AIServiceUnavailableException(f"AI Service error: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            logger.error(f"AI Service detection request failed: {e}")
            raise AIServiceUnavailableException(f"AI Service connection failed: {e}") from e

    @classmethod
    def get_model_registry(cls) -> Dict[str, Any]:
        """
        Retrieve available models and active model versions from AI Service.
        GET /models
        """
        base = cls.get_base_url()
        session = cls.get_session()
        try:
            resp = session.get(f"{base}/models", headers=cls.get_headers(), timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service models endpoint returned HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Failed to fetch model registry: {e}") from e

    @classmethod
    def get_fallback_status(cls) -> Dict[str, Any]:
        """
        Retrieve fallback engine operational readiness and heuristics.
        GET /fallback/status
        """
        base = cls.get_base_url()
        session = cls.get_session()
        try:
            resp = session.get(f"{base}/fallback/status", headers=cls.get_headers(), timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service fallback status returned HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Failed to fetch fallback status: {e}") from e
