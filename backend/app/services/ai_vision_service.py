import os
import time
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image, ImageStat
import numpy as np
import torch
import torchvision.transforms as transforms

from app.core.config import settings
from app.services.ai_fallback_service import AIFallbackService

logger = logging.getLogger("wastedash.ai_vision")

# Canonical 11 GCC Municipal Solid Waste Taxonomy
MUNICIPAL_CATEGORIES = [
    "Organic Waste",
    "Food Waste",
    "Plastic",
    "Paper",
    "Cardboard",
    "Glass",
    "Metal",
    "Textile Waste",
    "E-Waste",
    "Hazardous Waste",
    "Mixed Waste"
]

PRIMARY_CATEGORIES = MUNICIPAL_CATEGORIES

CATEGORY_HIERARCHY = {
    "E-Waste": {
        "Communication Devices": ["Mobile Phone", "Smartphone", "Feature Phone", "Tablet"],
        "Computers": ["Laptop", "Keyboard", "Mouse", "Computer Monitor", "Computer Parts"],
        "Power and Charging": ["Battery", "Power Bank", "Charger", "Charging Adapter", "USB Cable"],
        "Audio Devices": ["Earphones", "Headphones", "Speakers"],
        "Electronic Components": ["Circuit Board", "Electronic Components"]
    },
    "Plastic": {
        "Rigid Plastic": ["Plastic Bottle (PET)", "Plastic Food Container", "HDPE Jug"],
        "Flexible Plastic": ["Single-use Polybag", "Plastic Packaging Film", "Plastic Straw / Cutlery"]
    },
    "Paper": {
        "Paper & Board": ["Office Printing Paper", "Newspaper & Magazines", "Corrugated Box", "Paper Cup"]
    },
    "Cardboard": {
        "Boxes": ["Corrugated Cardboard Box", "Kraft Shipping Carton"]
    },
    "Glass": {
        "Glassware": ["Glass Beverage Bottle", "Glass Condiment Jar", "Broken Glassware", "Cosmetic Bottle"]
    },
    "Metal": {
        "Cans & Scrap": ["Aluminum Beverage Can", "Tin Food Can", "Scrap Metal Cutlery", "Aerosol Can"]
    },
    "Organic Waste": {
        "Wet & Green": ["Garden Leaves & Twigs", "Vegetable & Fruit Peels", "Cooked Plate Leftovers", "Coconut Husk"]
    },
    "Food Waste": {
        "Kitchen Wet": ["Plate Scraps", "Vegetable Trimmings", "Fruit Scraps"]
    },
    "Textile Waste": {
        "Apparel & Fabric": ["Discarded Cotton Shirt", "Synthetic Fabric Remnants", "Old Jute Bag"]
    },
    "Hazardous Waste": {
        "Chemical & Bio": ["Medical Syringe / Vial", "Paint Solvent Can", "Insecticide Spray", "Fluorescent Tube"]
    },
    "Mixed Waste": {
        "Unsorted": ["Unsegregated Mixed Bag", "Soiled Packaging Mix", "Street Sweepings"]
    }
}

ITEM_TO_PRIMARY_CATEGORY = {}
ALL_LEVEL2_ITEMS = []
for primary, subcats in CATEGORY_HIERARCHY.items():
    for subcat_name, items in subcats.items():
        for item in items:
            ITEM_TO_PRIMARY_CATEGORY[item] = primary
            ALL_LEVEL2_ITEMS.append(item)

CATEGORY_COLORS = {
    "E-Waste": "#8B5CF6",       # Purple
    "Plastic": "#3B82F6",       # Blue
    "Metal": "#64748B",         # Slate
    "Organic Waste": "#10B981", # Emerald
    "Food Waste": "#84CC16",    # Lime
    "Glass": "#F59E0B",         # Amber
    "Paper": "#EAB308",         # Yellow
    "Cardboard": "#D97706",     # Ochre
    "Hazardous Waste": "#EF4444",# Rose
    "Textile Waste": "#EC4899", # Pink
    "Mixed Waste": "#64748B",   # Gray
}

# External Dataset Class Mapping to GCC Categories
EXTERNAL_CLASS_MAPPING = {
    "cardboard": ("Cardboard", "Corrugated Cardboard Box"),
    "glass": ("Glass", "Glass Bottle / Jar"),
    "matel": ("Metal", "Scrap Metal / Can"),
    "metal": ("Metal", "Scrap Metal / Can"),
    "plastic": ("Plastic", "Plastic Container / Bottle"),
    "paper": ("Paper", "Paper / Newspaper"),
    "trash": ("Mixed Waste", "General Mixed Waste"),
    "biodegradable": ("Organic Waste", "Organic Garden / Food Waste"),
    "organic": ("Organic Waste", "Organic Waste"),
    "food": ("Food Waste", "Food Waste Leftovers"),
    "e-waste": ("E-Waste", "Electronic Component / Device"),
    "electronics": ("E-Waste", "Electronic Appliance"),
    "battery": ("E-Waste", "Battery / Cell"),
    "clothes": ("Textile Waste", "Textile Apparel"),
    "textile": ("Textile Waste", "Textile Fabric"),
    "medical": ("Hazardous Waste", "Medical / Hazardous Waste")
}

class BaseInferenceEngine:
    def __init__(self, version: str = "v2.1"):
        self.version = version
        self.device = torch.device("cpu")
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        raise NotImplementedError

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        raise NotImplementedError


class YOLOv8InferenceEngine(BaseInferenceEngine):
    """
    Ultralytics YOLOv8 Neural Object Detector with real bounding box regression
    and multi-class localization.
    """
    def __init__(self, weights_path: Optional[str] = None, version: str = "v2.1"):
        self.weights_path = weights_path or os.path.join(settings.MODELS_DIR, "yolov8_waste.pt")
        super().__init__(version=version)

    def load_model(self):
        try:
            from ultralytics import YOLO
            if os.path.exists(self.weights_path):
                self.model = YOLO(self.weights_path)
                self.is_loaded = True
                logger.info(f"Loaded YOLOv8 model from {self.weights_path}")
            else:
                logger.warning(f"YOLO weights not found at {self.weights_path}. Model load deferred.")
                self.model = None
                self.is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        t0 = time.time()
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "YOLO model not loaded"}

        # Run Ultralytics inference
        results = self.model(image, verbose=False)
        latency_ms = round((time.time() - t0) * 1000, 2)

        detections = []
        w, h = image.size

        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                # Normalized coordinates [ymin, xmin, ymax, xmax]
                xyxy = box.xyxy[0].tolist()
                xmin = round(max(0.0, min(1.0, xyxy[0] / w)), 4)
                ymin = round(max(0.0, min(1.0, xyxy[1] / h)), 4)
                xmax = round(max(0.0, min(1.0, xyxy[2] / w)), 4)
                ymax = round(max(0.0, min(1.0, xyxy[3] / h)), 4)

                conf = round(float(box.conf[0].item()), 4)
                cls_id = int(box.cls[0].item())
                raw_name = self.model.names.get(cls_id, "trash").lower()

                cat, item_name = EXTERNAL_CLASS_MAPPING.get(raw_name, ("Mixed Waste", raw_name.title()))
                color = CATEGORY_COLORS.get(cat, "#3B82F6")

                detections.append({
                    "object_name": item_name,
                    "raw_class": raw_name,
                    "waste_category": cat,
                    "confidence": conf,
                    "confidence_pct": int(conf * 100),
                    "bounding_box": [ymin, xmin, ymax, xmax],
                    "bbox_xywh": [xmin, ymin, round(xmax - xmin, 4), round(ymax - ymin, 4)],
                    "color": color
                })

        return {
            "success": True,
            "latency_ms": latency_ms,
            "detections": detections,
            "count": len(detections)
        }


class TorchvisionClassifierEngine(BaseInferenceEngine):
    """
    MobileNetV3 PyTorch Classifier fine-tuned across 11 municipal categories.
    Used for full-frame classification, single-object verification, and continuous retraining.
    """
    def __init__(self, weights_path: Optional[str] = None, version: str = "v2.1"):
        self.weights_path = weights_path or os.path.join(settings.MODELS_DIR, f"classifier_{version}.pt")
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        super().__init__(version=version)

    def load_model(self):
        try:
            import torchvision.models as models
            import torch.nn as nn
            self.model = models.mobilenet_v3_small(weights=None)
            self.model.classifier[3] = nn.Linear(self.model.classifier[3].in_features, len(MUNICIPAL_CATEGORIES))

            if os.path.exists(self.weights_path):
                state_dict = torch.load(self.weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                logger.info(f"Loaded classifier weights from {self.weights_path}")
            else:
                # Pretrained feature extractor backbone initialization
                base_pretrained = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
                # Transfer backbone weights
                self.model.features.load_state_dict(base_pretrained.features.state_dict())
                os.makedirs(os.path.dirname(self.weights_path), exist_ok=True)
                torch.save(self.model.state_dict(), self.weights_path)
                logger.info(f"Initialized new baseline weights at {self.weights_path}")

            self.model.eval()
            self.is_loaded = True
        except Exception as e:
            logger.error(f"Failed to load MobileNet classifier: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        t0 = time.time()
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "Classifier model not loaded"}

        try:
            tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1)[0]

            top_probs, top_indices = torch.topk(probs, k=3)
            latency_ms = round((time.time() - t0) * 1000, 2)

            top_cat = MUNICIPAL_CATEGORIES[top_indices[0].item()]
            top_conf = round(top_probs[0].item(), 4)

            top_predictions = []
            for p, idx in zip(top_probs.tolist(), top_indices.tolist()):
                top_predictions.append({
                    "waste_category": MUNICIPAL_CATEGORIES[idx],
                    "confidence": round(p, 4),
                    "confidence_pct": int(p * 100)
                })

            return {
                "success": True,
                "latency_ms": latency_ms,
                "top_category": top_cat,
                "confidence": top_conf,
                "confidence_pct": int(top_conf * 100),
                "top_predictions": top_predictions
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AIVisionService:
    """
    Centralized Municipal AI Vision Orchestrator.
    Manages active model versions, runs real YOLOv8 object localization or MobileNet classification,
    and extracts 128-d visual feature embeddings for personal AI memory.
    """
    _active_yolo_engine: Optional[YOLOv8InferenceEngine] = None
    _active_classifier_engine: Optional[TorchvisionClassifierEngine] = None
    _active_version: str = "v2.1"

    @classmethod
    def get_engines(cls) -> Tuple[YOLOv8InferenceEngine, TorchvisionClassifierEngine]:
        if cls._active_yolo_engine is None:
            cls._active_yolo_engine = YOLOv8InferenceEngine(version=cls._active_version)
        if cls._active_classifier_engine is None:
            cls._active_classifier_engine = TorchvisionClassifierEngine(version=cls._active_version)
        return cls._active_yolo_engine, cls._active_classifier_engine

    @classmethod
    def switch_active_model(cls, version: str, weights_path: Optional[str] = None) -> bool:
        """Atomically switches the active inference model version and reloads weights."""
        try:
            cls._active_version = version
            cls._active_yolo_engine = YOLOv8InferenceEngine(weights_path=weights_path, version=version)
            cls._active_classifier_engine = TorchvisionClassifierEngine(weights_path=weights_path, version=version)
            logger.info(f"Switched active AI Vision model to {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch model to {version}: {e}")
            return False

    @staticmethod
    def calculate_image_hash(image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def calculate_blur_score(image: Image.Image) -> float:
        """Calculates sharpness score using Laplacian gradient variance."""
        try:
            gray = image.convert('L')
            arr = np.array(gray, dtype=np.float32)
            gy, gx = np.gradient(arr)
            grad_var = float(np.var(gx) + np.var(gy))
            stat = ImageStat.Stat(gray)
            std_dev = stat.stddev[0]
            normalized = min(100.0, max(5.0, (grad_var / 8.0) * 0.5 + std_dev * 0.5))
            return round(normalized, 1)
        except Exception:
            return 75.0

    @staticmethod
    def validate_image_quality(
        image: Image.Image,
        file_size_kb: float,
        existing_hashes: List[str],
        current_hash: str
    ) -> Tuple[bool, str, float]:
        width, height = image.size
        if width < 120 or height < 120:
            return False, "Image resolution too low (minimum 120x120 required)", 15.0

        if file_size_kb < 3.0:
            return False, "File size suspiciously small (<3KB)", 10.0

        if current_hash in existing_hashes:
            return False, "Duplicate image already exists in dataset", 50.0

        blur = AIVisionService.calculate_blur_score(image)
        if blur < 22.0:
            return False, f"Image appears too blurry (sharpness score {blur}/100)", blur

        return True, "Image passed quality validation pipeline", blur

    @staticmethod
    def extract_image_embedding(image: Image.Image) -> List[float]:
        """
        Extracts a dense 128-dimensional normalized visual feature embedding vector
        capturing spatial color distribution, edge gradients, and morphology.
        """
        try:
            rgb_img = image.convert("RGB").resize((64, 64))
            arr = np.array(rgb_img, dtype=np.float32) / 255.0

            # 1. 8x8 Grid Spatial Luminance (64 dims)
            grid_img = rgb_img.resize((8, 8), Image.Resampling.BOX)
            grid_arr = np.array(grid_img, dtype=np.float32) / 255.0
            luminance = (0.299 * grid_arr[:, :, 0] + 0.587 * grid_arr[:, :, 1] + 0.114 * grid_arr[:, :, 2]).flatten()

            # 2. Quadrant Directional Edge Gradients (32 dims)
            gray = image.convert("L").resize((64, 64))
            gray_arr = np.array(gray, dtype=np.float32)
            edge_features = []
            for qy in [0, 32]:
                for qx in [0, 32]:
                    quad = gray_arr[qy:qy+32, qx:qx+32]
                    edge_features.extend([
                        float(np.mean(np.abs(np.diff(quad, axis=1)))),
                        float(np.var(quad)),
                        float(np.mean(np.abs(np.diff(quad, axis=0)))),
                        float(np.var(np.diff(quad, axis=0))),
                        float(np.mean(np.abs(quad[1:, 1:] - quad[:-1, :-1]))),
                        float(np.mean(np.abs(quad[1:, :-1] - quad[:-1, 1:]))),
                        float(np.max(quad) - np.min(quad)),
                        float(np.std(quad))
                    ])
            edge_features = np.array(edge_features[:32], dtype=np.float32)

            # 3. Geometric Morphology & Aspect Ratio (16 dims)
            w, h = image.size
            aspect_ratio = float(w) / float(max(1, h))
            morph_features = np.array([
                aspect_ratio,
                float(h) / float(max(1, w)),
                float(1.6 <= aspect_ratio <= 2.4),
                float(1.25 <= aspect_ratio <= 1.55),
                float(0.85 <= aspect_ratio <= 1.15),
                float(np.mean(arr)),
                float(np.std(arr)),
                float(np.mean(arr[:, :, 0])),
                float(np.mean(arr[:, :, 1])),
                float(np.mean(arr[:, :, 2])),
                float(np.max(arr) - np.min(arr)),
                float(np.median(arr)),
                float(len(arr[arr > 0.8]) / arr.size),
                float(len(arr[arr < 0.2]) / arr.size),
                float(np.var(arr[:, :, 0])),
                float(np.var(arr[:, :, 1]))
            ], dtype=np.float32)

            # 4. Texture frequency bands (16 dims)
            h_diffs = np.abs(np.diff(gray_arr, axis=1))
            tex_features = []
            for band in range(8):
                band_strip = h_diffs[band*8:(band+1)*8, :]
                tex_features.append(float(np.mean(band_strip)))
                tex_features.append(float(np.std(band_strip)))
            tex_features = np.array(tex_features[:16], dtype=np.float32)

            dense_vec = np.concatenate([luminance, edge_features, morph_features, tex_features])
            norm = np.linalg.norm(dense_vec)
            if norm > 0:
                dense_vec = dense_vec / norm

            return [round(float(x), 6) for x in dense_vec.tolist()]
        except Exception:
            return [0.0] * 128

    @staticmethod
    def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        try:
            a = np.array(vec1, dtype=np.float32)
            b = np.array(vec2, dtype=np.float32)
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            if denom == 0:
                return 0.0
            cos_sim = float(np.dot(a, b) / denom)
            return round(max(0.0, min(1.0, (cos_sim + 1.0) / 2.0)), 4)
        except Exception:
            return 0.0

    @classmethod
    def _run_primary_model(cls, image: Image.Image) -> Optional[Dict[str, Any]]:
        """Executes primary deep learning inference (Remote AI Microservice or local YOLO/MobileNet) on input image."""
        # Check if remote AI microservice is configured
        if settings.AI_INFERENCE_URL and settings.AI_INFERENCE_URL.strip():
            try:
                import io
                import requests
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                buf.seek(0)
                headers = {}
                if settings.AI_INFERENCE_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.AI_INFERENCE_API_KEY}"
                    headers["X-API-Key"] = settings.AI_INFERENCE_API_KEY
                endpoint = f"{settings.AI_INFERENCE_URL.rstrip('/')}/predict"
                resp = requests.post(
                    endpoint,
                    files={"file": ("frame.jpg", buf.getvalue(), "image/jpeg")},
                    headers=headers,
                    timeout=settings.INFERENCE_TIMEOUT_SECONDS
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cat = data.get("predicted_category") or data.get("category")
                    conf = float(data.get("confidence", 0.0))
                    return {
                        "predicted_category": cat,
                        "detected_item": data.get("detected_item") or data.get("item", f"{cat} Item"),
                        "confidence": conf,
                        "confidence_pct": int(data.get("confidence_pct", conf * 100)),
                        "bounding_box": data.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
                        "bbox_xywh": data.get("bbox_xywh", [0.1, 0.1, 0.8, 0.8]),
                        "color": data.get("color", CATEGORY_COLORS.get(cat, "#3B82F6")),
                        "classification_method": "remote_ai_service",
                        "latency_ms": data.get("latency_ms", 45.0)
                    }
                else:
                    logger.warning(f"Remote AI inference failed with HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Remote AI inference request exception: {e}")

        yolo_engine, classifier_engine = cls.get_engines()
        if yolo_engine and yolo_engine.is_loaded:
            yolo_res = yolo_engine.predict(image)
            if yolo_res.get("success") and yolo_res.get("detections"):
                top_det = yolo_res["detections"][0]
                return {
                    "predicted_category": top_det.get("waste_category"),
                    "detected_item": top_det.get("object_name"),
                    "confidence": top_det.get("confidence", 0),
                    "confidence_pct": top_det.get("confidence_pct", 0),
                    "bounding_box": top_det.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
                    "bbox_xywh": top_det.get("bbox_xywh", [0.1, 0.1, 0.8, 0.8]),
                    "color": top_det.get("color", "#3B82F6"),
                    "classification_method": "primary_ai",
                    "latency_ms": yolo_res.get("latency_ms", 15.0),
                    "all_detections": yolo_res.get("detections")
                }

        if classifier_engine and classifier_engine.is_loaded:
            cls_res = classifier_engine.predict(image)
            if cls_res.get("success"):
                top_cat = cls_res.get("top_category")
                conf = cls_res.get("confidence", 0)
                return {
                    "predicted_category": top_cat,
                    "detected_item": f"{top_cat} Material",
                    "confidence": conf,
                    "confidence_pct": int(conf * 100),
                    "bounding_box": [0.1, 0.1, 0.9, 0.9],
                    "bbox_xywh": [0.1, 0.1, 0.8, 0.8],
                    "color": CATEGORY_COLORS.get(top_cat, "#3B82F6"),
                    "classification_method": "primary_ai",
                    "latency_ms": cls_res.get("latency_ms", 25.0)
                }
        return None

    @classmethod
    def detect_and_classify(
        cls,
        image: Image.Image,
        filename_hint: str = "",
        force_fallback: bool = False,
        primary_should_fail: bool = False
    ) -> Dict[str, Any]:
        """
        Centralized Municipal AI Vision Orchestrator with Mandatory Fallback:
        1. Validates and extracts 128-d visual feature embedding.
        2. Tries primary neural model (Ultralytics YOLO / MobileNet) unless force_fallback is set.
        3. If primary succeeds with confidence >= threshold and valid category, returns primary result.
        4. If primary fails, times out, raises exception, or yields low confidence:
           Activates mandatory classical CV and rule-based heuristic fallback algorithm!
        5. Returns structured diagnostic response detailing method, fallback status, and confidence.
        """
        t0 = time.time()
        embedding = cls.extract_image_embedding(image)

        primary_status = "unavailable"
        primary_result = None

        # Step 1: Attempt Primary Deep Learning Neural Inference
        if not force_fallback and not primary_should_fail:
            try:
                prim = cls._run_primary_model(image)
                if prim and prim.get("confidence", 0) >= settings.AI_CONFIDENCE_THRESHOLD and prim.get("predicted_category") in MUNICIPAL_CATEGORIES:
                    primary_status = "success"
                    primary_result = {
                        "predicted_category": prim["predicted_category"],
                        "detected_item": prim.get("detected_item", f"{prim['predicted_category']} Item"),
                        "confidence": prim["confidence"],
                        "confidence_pct": prim.get("confidence_pct", int(prim["confidence"] * 100)),
                        "bounding_box": prim.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
                        "bbox_xywh": prim.get("bbox_xywh", [0.1, 0.1, 0.8, 0.8]),
                        "color": prim.get("color", CATEGORY_COLORS.get(prim["predicted_category"], "#3B82F6")),
                        "classification_method": prim.get("classification_method", "primary_ai"),
                        "primary_model_status": "success",
                        "fallback_used": False,
                        "requires_review": False,
                        "latency_ms": prim.get("latency_ms", round((time.time() - t0) * 1000, 2)),
                        "stage_notes": f"Primary neural model ({cls._active_version}) executed successfully"
                    }
                elif prim:
                    primary_status = "low_confidence" if prim.get("confidence", 0) < settings.AI_CONFIDENCE_THRESHOLD else "invalid_label"
            except Exception as e:
                logger.warning(f"Primary model inference exception: {e}")
                primary_status = "exception_raised"
        elif primary_should_fail:
            primary_status = "simulated_primary_failure"
        else:
            primary_status = "forced_fallback"

        # If primary succeeded with high confidence, return primary result
        if primary_result is not None:
            primary_result.update({
                "model_version": cls._active_version,
                "model_framework": "PyTorch 2.2 / YOLOv8-Waste",
                "embedding": embedding,
                "status": "High Confidence Detection",
                "is_low_confidence": False,
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            })
            return primary_result

        # Step 2: Primary Model Unusable/Failed -> Trigger Mandatory Fallback Algorithm
        logger.info(f"Primary AI model unusable (status: {primary_status}). Activating classical CV fallback algorithm.")
        try:
            fallback_res = AIFallbackService.classify_with_fallback(image, filename_hint=filename_hint)
        except Exception as e:
            logger.error(f"Fallback classification exception: {e}")
            return {
                "success": False,
                "predicted_category": "unknown",
                "detected_item": "Unclassified Waste Item",
                "confidence": 0.0,
                "confidence_pct": 0,
                "classification_method": "emergency_fallback",
                "primary_model_status": primary_status,
                "fallback_used": True,
                "requires_review": True,
                "bounding_box": [0.1, 0.1, 0.9, 0.9],
                "bbox_xywh": [0.1, 0.1, 0.8, 0.8],
                "color": "#94A3B8",
                "embedding": embedding,
                "fallback_details": {"error": str(e), "primary_status": primary_status},
                "stage_notes": "Emergency recovery fallback activated after primary & secondary errors",
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }

        fallback_res.update({
            "primary_model_status": primary_status,
            "model_version": cls._active_version,
            "model_framework": "OpenCV Classical CV / Heuristic Fallback",
            "embedding": embedding,
            "status": "Fallback Heuristic Classification" if not fallback_res.get("requires_review") else "Uncertain — Needs Verification",
            "is_low_confidence": fallback_res.get("requires_review", True),
            "secondary_prediction": {
                "detected_item": "Mixed Waste",
                "predicted_category": "Mixed Waste",
                "confidence": 0.20
            }
        })

        # Add estimated weight
        weight_map = {
            "E-Waste": 0.25, "Plastic": 0.08, "Paper": 0.05, "Cardboard": 0.35,
            "Glass": 0.45, "Metal": 0.15, "Organic Waste": 0.60, "Food Waste": 0.50,
            "Textile Waste": 0.30, "Hazardous Waste": 0.20, "Mixed Waste": 0.40,
            "unknown": 0.25
        }
        fallback_res["estimated_weight_kg"] = weight_map.get(fallback_res["predicted_category"], 0.30)

        return fallback_res
