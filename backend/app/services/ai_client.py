"""
Dedicated Backend AI Service Client for WasteDash.
Communicates with the standalone, independently deployed WasteDash AI Microservice.

Supports:
- Localhost co-located deployment: AI_API_BASE_URL=http://127.0.0.1:8001 (or 8000)
- Local Area Network (LAN) deployment: AI_API_BASE_URL=http://<lan-ip>:8001
- Remote / Cloud deployment with configurable base URL
- Connection pooling via requests.Session and HTTPAdapter
- Granular timeouts: separate connect (3s) and read timeouts
- Safe error handling without crashing caller workflows
- Security: server-side only tokens, image size limits, URL scheme validation
- Backward compatibility with legacy method signatures and response schemas
"""

import io
import time
import logging
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple, Union
from PIL import Image
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings

logger = logging.getLogger("wastedash.ai_client")


class AIServiceException(Exception):
    """Base exception for AI microservice communication errors."""
    pass


class AIServiceUnavailableException(AIServiceException):
    """Raised when standalone AI service is unreachable, timed out, or returns a 5xx error."""
    pass


class AIServiceTimeoutException(AIServiceUnavailableException):
    """Raised specifically when a connection or read timeout expires."""
    pass


class AIServiceResponseException(AIServiceException):
    """Raised when standalone AI service returns a 4xx validation or processing error."""
    pass


class AIServiceValidationException(AIServiceException):
    """Raised when input payload fails client-side safety or size validation."""
    pass


class AIServiceClient:
    """
    Dedicated HTTP Client for communicating with the standalone WasteDash AI API.

    Features:
      - Connection pooling via requests.Session with bounded retries on idempotent calls.
      - Configurable base URL: settings.AI_API_BASE_URL (with fallback aliases).
      - Separate connect timeout (fast fail if offline) and read timeout.
      - Strict URL validation (only http and https permitted).
      - Payload validation (file size, dimensions) before network transmission.
      - Never leaks credentials, binary payloads, or filesystem paths.
    """
    _session: Optional[requests.Session] = None

    @classmethod
    def normalize_url(cls, raw_url: Optional[str]) -> str:
        """
        Validates and sanitizes target AI API base URL.
        Only http and https schemes are permitted. Trailing slashes are stripped.
        """
        if not raw_url:
            return ""
        cleaned = raw_url.strip()
        if cleaned.lower() in ("none", "disabled", "false", "null", "0", ""):
            return ""

        # Check if scheme is specified
        if "://" in cleaned:
            scheme = cleaned.split("://", 1)[0].lower()
            if scheme not in ("http", "https"):
                raise AIServiceValidationException(
                    f"Invalid AI API URL scheme '{scheme}'. Only http and https are permitted."
                )
        else:
            cleaned = f"http://{cleaned}"

        parsed = urllib.parse.urlparse(cleaned)
        if parsed.scheme not in ("http", "https"):
            raise AIServiceValidationException(
                f"Invalid AI API URL scheme '{parsed.scheme}'. Only http and https are permitted."
            )
        if not parsed.netloc:
            raise AIServiceValidationException(f"Invalid AI API URL '{raw_url}': missing host.")

        # Strip userinfo (embedded credentials) if present for safety
        host_port = parsed.netloc.split("@")[-1]
        normalized = f"{parsed.scheme}://{host_port}{parsed.path}".rstrip("/")
        return normalized

    @classmethod
    def get_base_url(cls) -> str:
        """
        Retrieves normalized AI microservice base URL.
        Prioritizes AI_API_BASE_URL, with fallback to legacy aliases.
        """
        raw = (
            getattr(settings, "AI_API_BASE_URL", None)
            or getattr(settings, "AI_SERVICE_BASE_URL", None)
            or getattr(settings, "AI_INFERENCE_URL", None)
            or "http://127.0.0.1:8001"
        )
        return cls.normalize_url(raw)

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if a valid, non-empty AI API base URL is configured."""
        try:
            url = cls.get_base_url()
            return bool(url)
        except Exception:
            return False

    @classmethod
    def get_session(cls) -> requests.Session:
        """Returns shared requests.Session configured with connection pooling and retries."""
        if cls._session is None:
            s = requests.Session()
            max_retries_count = getattr(settings, "AI_API_MAX_RETRIES", 2)
            retries = Retry(
                total=max_retries_count,
                backoff_factor=0.3,
                status_forcelist=[502, 503, 504],
                allowed_methods=["GET", "HEAD", "OPTIONS"]
            )
            pool_conn = getattr(settings, "AI_API_POOL_CONNECTIONS", 10)
            pool_max = getattr(settings, "AI_API_POOL_MAXSIZE", 25)
            adapter = HTTPAdapter(
                pool_connections=pool_conn,
                pool_maxsize=pool_max,
                max_retries=retries
            )
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            cls._session = s
        return cls._session

    @classmethod
    def get_headers(cls, is_admin: bool = False) -> Dict[str, str]:
        """
        Generates server-side authentication headers.
        Injects both X-API-Key and Authorization: Bearer for compatibility.
        Never returns or logs these keys in client responses.
        """
        headers = {}
        if is_admin:
            key = getattr(settings, "AI_ADMIN_API_KEY", "") or getattr(settings, "AI_API_KEY", "")
        else:
            key = (
                getattr(settings, "AI_API_KEY", "")
                or getattr(settings, "AI_SERVICE_API_KEY", "")
                or getattr(settings, "AI_INFERENCE_API_KEY", "")
            )

        if key and key.strip():
            k = key.strip()
            headers["X-API-Key"] = k
            headers["Authorization"] = f"Bearer {k}"
        return headers

    @classmethod
    def get_timeouts(cls, custom_read_timeout: Optional[float] = None) -> Tuple[float, float]:
        """
        Returns (connect_timeout, read_timeout) tuple.
        Connect timeout is kept short (e.g. 3.0s) so unreachable LAN/localhost IPs fail fast.
        """
        conn_timeout = getattr(settings, "AI_API_CONNECT_TIMEOUT_SECONDS", 3.0)
        read_timeout = custom_read_timeout or getattr(settings, "AI_API_TIMEOUT_SECONDS", getattr(settings, "INFERENCE_TIMEOUT_SECONDS", 15.0))
        return (float(conn_timeout), float(read_timeout))

    @classmethod
    def _prepare_image_payload(
        cls,
        image: Union[Image.Image, bytes],
        max_size_mb: Optional[float] = None
    ) -> bytes:
        """Validates and prepares image bytes in memory."""
        limit_mb = max_size_mb or getattr(settings, "MAX_IMAGE_SIZE_MB", 15.0)
        max_bytes = int(limit_mb * 1024 * 1024)

        if isinstance(image, bytes):
            img_bytes = image
            if len(img_bytes) == 0:
                raise AIServiceValidationException("Image payload is empty (0 bytes).")
            if len(img_bytes) > max_bytes:
                raise AIServiceValidationException(
                    f"Image payload ({len(img_bytes)} bytes) exceeds maximum limit of {limit_mb} MB."
                )
            try:
                # Validate image header
                with Image.open(io.BytesIO(img_bytes)) as pil:
                    pil.verify()
            except Exception as e:
                raise AIServiceValidationException(f"Invalid image format: {e}") from e
            return img_bytes

        elif isinstance(image, Image.Image):
            w, h = image.size
            if w < 10 or h < 10:
                raise AIServiceValidationException(f"Image dimensions too small ({w}x{h}). Minimum 10x10.")
            if w > 4096 or h > 4096:
                raise AIServiceValidationException(f"Image dimensions too large ({w}x{h}). Maximum 4096x4096.")

            buf = io.BytesIO()
            rgb = image.convert("RGB")
            rgb.save(buf, format="JPEG", quality=90)
            img_bytes = buf.getvalue()
            if len(img_bytes) > max_bytes:
                raise AIServiceValidationException(
                    f"Encoded image ({len(img_bytes)} bytes) exceeds limit of {limit_mb} MB."
                )
            return img_bytes

        else:
            raise AIServiceValidationException(f"Unsupported image type: {type(image)}")

    # -------------------------------------------------------------------------
    # HEALTH & READINESS PROBING
    # -------------------------------------------------------------------------

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """
        Check health and readiness of standalone AI Microservice.
        Probes GET /api/v1/ai/health (with fallback to GET /health).
        Raises AIServiceUnavailableException or AIServiceResponseException on failure.
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("Standalone AI API URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=min(5.0, getattr(settings, "AI_API_TIMEOUT_SECONDS", 5.0)))

        try:
            # 1. Primary path: /api/v1/ai/health
            resp = session.get(f"{base}/api/v1/ai/health", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code == 200:
                return resp.json()

            # 2. Legacy fallback path: /health
            resp = session.get(f"{base}/health", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code == 200:
                return resp.json()

            raise AIServiceResponseException(
                f"AI Service health check returned HTTP {resp.status_code}"
            )
        except requests.exceptions.Timeout as e:
            logger.warning(f"AI Service health check timed out at {base}: {e}")
            raise AIServiceTimeoutException(f"Standalone AI microservice timed out at {base}") from e
        except requests.RequestException as e:
            logger.warning(f"AI Service health check connection failed at {base}: {e}")
            raise AIServiceUnavailableException(f"Standalone AI microservice unreachable at {base}") from e

    @classmethod
    def get_health_summary(cls, timeout: float = 2.0) -> Dict[str, Any]:
        """
        Safe, non-raising health probe designed for the main backend /api/health endpoint.
        Distinguishes reachability from model readiness.
        Never leaks secret keys, filesystem paths, or host tokens.
        """
        t0 = time.time()
        base = cls.get_base_url()
        if not base:
            return {
                "configured": False,
                "reachable": False,
                "inference_ready": False,
                "status": "not_configured",
                "message": "Standalone AI API is not configured (local models or CV fallback active)."
            }

        session = cls.get_session()
        safe_timeouts = (min(2.0, timeout), timeout)

        try:
            resp = session.get(f"{base}/api/v1/ai/health", headers=cls.get_headers(), timeout=safe_timeouts)
            if resp.status_code != 200:
                resp = session.get(f"{base}/health", headers=cls.get_headers(), timeout=safe_timeouts)

            latency = round((time.time() - t0) * 1000, 2)
            if resp.status_code == 200:
                data = resp.json()
                # Sanitize active_models: strip full filesystem paths to avoid server host info leakage
                raw_models = data.get("active_models", {})
                sanitized_models = {}
                if isinstance(raw_models, dict):
                    for m_key, m_val in raw_models.items():
                        if isinstance(m_val, dict):
                            clean_m = dict(m_val)
                            clean_m.pop("weights_path", None)
                            sanitized_models[m_key] = clean_m
                        else:
                            sanitized_models[m_key] = m_val

                return {
                    "configured": True,
                    "reachable": True,
                    "inference_ready": bool(data.get("inference_ready", False)),
                    "status": data.get("status", "healthy"),
                    "version": data.get("version", "unknown"),
                    "device": data.get("device", "unknown"),
                    "active_models": sanitized_models,
                    "supported_tasks": data.get("supported_tasks", []),
                    "latency_ms": latency
                }
            else:
                return {
                    "configured": True,
                    "reachable": True,
                    "inference_ready": False,
                    "status": f"http_{resp.status_code}",
                    "latency_ms": latency
                }
        except requests.exceptions.Timeout:
            return {
                "configured": True,
                "reachable": False,
                "inference_ready": False,
                "status": "timed_out",
                "latency_ms": round((time.time() - t0) * 1000, 2)
            }
        except Exception:
            return {
                "configured": True,
                "reachable": False,
                "inference_ready": False,
                "status": "unreachable",
                "latency_ms": round((time.time() - t0) * 1000, 2)
            }

    # -------------------------------------------------------------------------
    # STILL IMAGE CLASSIFICATION (ResNet50)
    # -------------------------------------------------------------------------

    @classmethod
    def classify_image(
        cls,
        image: Union[Image.Image, bytes],
        upload_id: Optional[Union[str, int]] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submits still image for ResNet50 neural classification.
        Endpoint: POST /api/v1/ai/predict/image (fallback: POST /classify).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        img_bytes = cls._prepare_image_payload(image)
        session = cls.get_session()
        timeouts = cls.get_timeouts()
        upload_name = filename or f"upload_{upload_id or int(time.time()*1000)}.jpg"

        files = {"file": (upload_name, img_bytes, "image/jpeg")}
        headers = cls.get_headers()

        try:
            # 1. Primary endpoint: /api/v1/ai/predict/image
            resp = session.post(
                f"{base}/api/v1/ai/predict/image",
                files=files,
                headers=headers,
                timeout=timeouts
            )

            # 2. Legacy alias fallback if 404
            if resp.status_code == 404:
                files = {"file": (upload_name, img_bytes, "image/jpeg")}
                resp = session.post(
                    f"{base}/classify",
                    files=files,
                    headers=headers,
                    timeout=timeouts
                )

            if resp.status_code == 200:
                data = resp.json()
                return cls._normalize_prediction_response(data, default_task="image_classification")
            elif 400 <= resp.status_code < 500:
                raise AIServiceResponseException(
                    f"AI Service rejected image: HTTP {resp.status_code} - {resp.text}"
                )
            else:
                raise AIServiceUnavailableException(
                    f"AI Service error: HTTP {resp.status_code} - {resp.text}"
                )
        except requests.exceptions.Timeout as e:
            logger.warning(f"AI Service image classification timed out at {base}: {e}")
            raise AIServiceTimeoutException(f"AI Service classification timed out after {timeouts[1]}s") from e
        except requests.RequestException as e:
            logger.warning(f"AI Service image classification connection failed at {base}: {e}")
            raise AIServiceUnavailableException(f"AI Service connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # CAMERA / VIDEO FRAME OBJECT DETECTION (YOLO11n)
    # -------------------------------------------------------------------------

    @classmethod
    def detect_frame(
        cls,
        image: Union[Image.Image, bytes],
        frame_id: Optional[Union[str, int]] = None,
        conf_threshold: float = 0.25,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submits camera / video frame for YOLO11n object localization and bounding box regression.
        Endpoint: POST /api/v1/ai/predict/frame (fallback: POST /detect).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        img_bytes = cls._prepare_image_payload(image)
        session = cls.get_session()
        timeouts = cls.get_timeouts()
        frame_name = filename or f"frame_{frame_id or int(time.time()*1000)}.jpg"
        threshold_val = float(conf_threshold)

        # Include both confidence_threshold and conf_threshold in query for maximum cross-service compatibility
        query_params = f"confidence_threshold={threshold_val}&conf_threshold={threshold_val}"
        files = {"file": (frame_name, img_bytes, "image/jpeg")}
        headers = cls.get_headers()

        try:
            # 1. Primary endpoint: /api/v1/ai/predict/frame
            resp = session.post(
                f"{base}/api/v1/ai/predict/frame?{query_params}",
                files=files,
                headers=headers,
                timeout=timeouts
            )

            # 2. Legacy alias fallback if 404
            if resp.status_code == 404:
                files = {"file": (frame_name, img_bytes, "image/jpeg")}
                resp = session.post(
                    f"{base}/detect?{query_params}",
                    files=files,
                    headers=headers,
                    timeout=timeouts
                )

            if resp.status_code == 200:
                data = resp.json()
                return cls._normalize_prediction_response(data, default_task="object_detection")
            elif 400 <= resp.status_code < 500:
                raise AIServiceResponseException(
                    f"AI Service rejected frame: HTTP {resp.status_code} - {resp.text}"
                )
            else:
                raise AIServiceUnavailableException(
                    f"AI Service error: HTTP {resp.status_code} - {resp.text}"
                )
        except requests.exceptions.Timeout as e:
            logger.warning(f"AI Service frame detection timed out at {base}: {e}")
            raise AIServiceTimeoutException(f"AI Service detection timed out after {timeouts[1]}s") from e
        except requests.RequestException as e:
            logger.warning(f"AI Service frame detection connection failed at {base}: {e}")
            raise AIServiceUnavailableException(f"AI Service connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # BATCH PREDICTION
    # -------------------------------------------------------------------------

    @classmethod
    def predict_batch(
        cls,
        images: List[Tuple[str, bytes]],
        task: str = "auto",
        conf_threshold: float = 0.25
    ) -> Dict[str, Any]:
        """
        Submits multiple images for batch inference.
        Endpoint: POST /api/v1/ai/predict/batch
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=30.0)

        files = [
            ("files", (fname, bts, "image/jpeg")) for fname, bts in images
        ]
        headers = cls.get_headers()

        try:
            resp = session.post(
                f"{base}/api/v1/ai/predict/batch?task={task}&confidence_threshold={conf_threshold}",
                files=files,
                headers=headers,
                timeout=timeouts
            )
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service batch failed: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"AI Service batch connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # AUTOMATED SORTING RECOMMENDATION CONTRACT
    # -------------------------------------------------------------------------

    @classmethod
    def get_sorting_recommendation(
        cls,
        category: str,
        confidence: float,
        detected_item: Optional[str] = None,
        device_id: Optional[str] = "DEFAULT_CONVEYOR_1",
        device_ready: bool = True
    ) -> Dict[str, Any]:
        """
        Queries AI service for automated sorting decision and bin destination.
        Endpoint: POST /api/v1/ai/sorting/recommend
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=5.0)

        payload = {
            "category": category,
            "confidence": float(confidence),
            "detected_item": detected_item or f"{category} Item",
            "device_id": device_id or "DEFAULT_CONVEYOR_1",
            "device_ready": device_ready
        }
        headers = cls.get_headers()
        headers["Content-Type"] = "application/json"

        try:
            resp = session.post(
                f"{base}/api/v1/ai/sorting/recommend",
                json=payload,
                headers=headers,
                timeout=timeouts
            )
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service sorting recommendation failed: HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"AI Service sorting connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # MODEL REGISTRY & LIFECYCLE MANAGEMENT
    # -------------------------------------------------------------------------

    @classmethod
    def get_model_registry(cls) -> Dict[str, Any]:
        """
        Retrieves catalog of models and active model versions from AI service.
        GET /api/v1/ai/models (fallback: GET /models).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=5.0)

        try:
            resp = session.get(f"{base}/api/v1/ai/models", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code != 200:
                resp = session.get(f"{base}/models", headers=cls.get_headers(), timeout=timeouts)

            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service models endpoint returned HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Failed to fetch model registry: {e}") from e

    @classmethod
    def get_active_models(cls) -> Dict[str, Any]:
        """
        Retrieves active classification and detection models.
        GET /api/v1/ai/models/active (fallback: GET /models/active).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=5.0)

        try:
            resp = session.get(f"{base}/api/v1/ai/models/active", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code != 200:
                resp = session.get(f"{base}/models/active", headers=cls.get_headers(), timeout=timeouts)

            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service active models returned HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Failed to fetch active models: {e}") from e

    @classmethod
    def get_fallback_status(cls) -> Dict[str, Any]:
        """
        Retrieves fallback engine operational readiness and heuristics.
        GET /api/v1/ai/fallback/status (fallback: GET /fallback/status).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=5.0)

        try:
            resp = session.get(f"{base}/api/v1/ai/fallback/status", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code != 200:
                resp = session.get(f"{base}/fallback/status", headers=cls.get_headers(), timeout=timeouts)

            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"AI Service fallback status returned HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Failed to fetch fallback status: {e}") from e

    @classmethod
    def activate_model(cls, model_id: str) -> Dict[str, Any]:
        """
        Requests activation of a validated model checkpoint on the AI service.
        POST /api/v1/ai/models/{model_id}/activate (requires AI_ADMIN_API_KEY).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=10.0)
        headers = cls.get_headers(is_admin=True)

        try:
            resp = session.post(f"{base}/api/v1/ai/models/{model_id}/activate", headers=headers, timeout=timeouts)
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"Model activation failed: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Model activation connection failed: {e}") from e

    @classmethod
    def rollback_model(cls, model_id: str) -> Dict[str, Any]:
        """
        Requests rollback of active model to previous validated checkpoint.
        POST /api/v1/ai/models/{model_id}/rollback (requires AI_ADMIN_API_KEY).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=10.0)
        headers = cls.get_headers(is_admin=True)

        try:
            resp = session.post(f"{base}/api/v1/ai/models/{model_id}/rollback", headers=headers, timeout=timeouts)
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"Model rollback failed: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Model rollback connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # RETRAINING PIPELINE INTEGRATION
    # -------------------------------------------------------------------------

    @classmethod
    def submit_training_job(
        cls,
        dataset_manifest_path: str,
        approval_id: str,
        approved_by: str,
        target_pipeline: str = "auto",
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 1e-4
    ) -> Dict[str, Any]:
        """
        Submits an authorized dataset manifest to the AI microservice for retraining.
        POST /api/v1/ai/training/jobs (requires AI_ADMIN_API_KEY).
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=10.0)

        payload = {
            "dataset_manifest_path": dataset_manifest_path,
            "approval_id": approval_id,
            "approved_by": approved_by,
            "target_pipeline": target_pipeline,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate
        }
        headers = cls.get_headers(is_admin=True)
        headers["Content-Type"] = "application/json"

        try:
            resp = session.post(f"{base}/api/v1/ai/training/jobs", json=payload, headers=headers, timeout=timeouts)
            if resp.status_code in (200, 201):
                return resp.json()
            raise AIServiceResponseException(f"Retraining job submission failed: HTTP {resp.status_code} - {resp.text}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Retraining submission connection failed: {e}") from e

    @classmethod
    def get_training_job_status(cls, job_id: str) -> Dict[str, Any]:
        """
        Polls retraining job status, progress %, and candidate evaluation report.
        GET /api/v1/ai/training/jobs/{job_id}
        """
        base = cls.get_base_url()
        if not base:
            raise AIServiceUnavailableException("AI microservice base URL is not configured.")

        session = cls.get_session()
        timeouts = cls.get_timeouts(custom_read_timeout=5.0)

        try:
            resp = session.get(f"{base}/api/v1/ai/training/jobs/{job_id}", headers=cls.get_headers(), timeout=timeouts)
            if resp.status_code == 200:
                return resp.json()
            raise AIServiceResponseException(f"Retraining status check failed: HTTP {resp.status_code}")
        except requests.RequestException as e:
            raise AIServiceUnavailableException(f"Retraining status connection failed: {e}") from e

    # -------------------------------------------------------------------------
    # RESPONSE NORMALIZATION ADAPTER
    # -------------------------------------------------------------------------

    @classmethod
    def _normalize_prediction_response(
        cls,
        raw: Dict[str, Any],
        default_task: str = "image_classification"
    ) -> Dict[str, Any]:
        """
        Guarantees that responses from the standalone AI API seamlessly conform
        to the fields and types expected by WasteDash service layers.
        """
        cat = raw.get("predicted_category") or raw.get("category") or "Unknown"
        conf = float(raw.get("confidence", 0.0))
        conf_pct = int(raw.get("confidence_pct", round(conf * 100)))

        bbox = raw.get("bounding_box", [0.1, 0.1, 0.9, 0.9])
        bbox_xywh = raw.get("bbox_xywh", [0.1, 0.1, 0.8, 0.8])

        detections = raw.get("detections", [])
        if detections and isinstance(detections, list):
            norm_dets = []
            for d in detections:
                if isinstance(d, dict):
                    norm_dets.append({
                        "object_name": d.get("object_name", "Detected Item"),
                        "raw_class": d.get("raw_class", "item"),
                        "waste_category": d.get("waste_category", cat),
                        "confidence": float(d.get("confidence", 0.0)),
                        "confidence_pct": int(d.get("confidence_pct", round(float(d.get("confidence", 0.0)) * 100))),
                        "bounding_box": d.get("bounding_box", bbox),
                        "bbox_xywh": d.get("bbox_xywh", bbox_xywh),
                        "color": d.get("color", "#3B82F6")
                    })
            detections = norm_dets

        return {
            "success": bool(raw.get("success", True)),
            "prediction_id": raw.get("prediction_id", f"PRED-{int(time.time()*1000)}"),
            "task": raw.get("task", default_task),
            "model_name": raw.get("model_name", "Standalone-AI-Service"),
            "model_version": raw.get("model_version", "v2.1"),
            "framework": raw.get("framework", "PyTorch 2.2"),
            "predicted_category": cat,
            "detected_item": raw.get("detected_item") or f"{cat} Item",
            "confidence": conf,
            "confidence_pct": conf_pct,
            "bounding_box": bbox,
            "bbox_xywh": bbox_xywh,
            "color": raw.get("color", "#3B82F6"),
            "top_predictions": raw.get("top_predictions", []),
            "count": raw.get("count", len(detections)),
            "detections": detections,
            "fallback_used": bool(raw.get("fallback_used", False)),
            "fallback_reason": raw.get("fallback_reason"),
            "classification_method": raw.get("classification_method", "standalone_neural_api"),
            "requires_review": bool(raw.get("requires_review", conf < 0.70)),
            "latency_ms": float(raw.get("latency_ms", 35.0)),
            "timestamp": raw.get("timestamp")
        }
