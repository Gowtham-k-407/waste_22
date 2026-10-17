import os
import io
import time
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image, ImageStat
import numpy as np
import torch
import torchvision.models as models
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
    "Food Waste": "#059669",    # Dark Emerald
    "Glass": "#F59E0B",         # Amber
    "Paper": "#EAB308",         # Yellow
    "Cardboard": "#D97706",     # Ochre
    "Hazardous Waste": "#EF4444",# Rose
    "Textile Waste": "#EC4899", # Pink
    "Mixed Waste": "#64748B",   # Gray
    "unknown": "#94A3B8"
}

# External COCO / Dataset Class Mapping to GCC Categories
EXTERNAL_CLASS_MAPPING = {
    "bottle": ("Plastic", "Plastic Bottle (PET)"),
    "wine glass": ("Glass", "Glass Bottle / Jar"),
    "cup": ("Glass", "Glass Beverage Cup"),
    "bowl": ("Glass", "Glass / Ceramic Bowl"),
    "vase": ("Glass", "Glass Container"),
    "fork": ("Metal", "Scrap Metal Cutlery (Fork)"),
    "knife": ("Metal", "Scrap Metal Cutlery (Knife)"),
    "spoon": ("Metal", "Scrap Metal Cutlery (Spoon)"),
    "scissors": ("Metal", "Scrap Metal Scissors"),
    "banana": ("Food Waste", "Fruit Scraps / Banana Peel"),
    "apple": ("Food Waste", "Fruit Scraps / Apple Core"),
    "sandwich": ("Food Waste", "Food Plate Leftovers"),
    "orange": ("Food Waste", "Fruit Peels / Citrus"),
    "broccoli": ("Food Waste", "Vegetable Trimmings / Broccoli"),
    "carrot": ("Food Waste", "Vegetable Peels / Carrot Trimmings"),
    "hot dog": ("Food Waste", "Cooked Food Leftovers"),
    "pizza": ("Food Waste", "Discarded Cooked Food"),
    "donut": ("Food Waste", "Bakery Waste"),
    "cake": ("Food Waste", "Discarded Food Scraps"),
    "potted plant": ("Organic Waste", "Garden Plant / Leaf Waste"),
    "book": ("Paper", "Clean Paper / Book"),
    "cell phone": ("E-Waste", "Mobile Phone / Smartphone"),
    "laptop": ("E-Waste", "Laptop Computer"),
    "mouse": ("E-Waste", "Computer Mouse"),
    "keyboard": ("E-Waste", "Computer Keyboard"),
    "remote": ("E-Waste", "Remote Control / Battery Item"),
    "tv": ("E-Waste", "Electronic Monitor / Display"),
    "microwave": ("E-Waste", "Consumer Electronic Appliance"),
    "oven": ("E-Waste", "Kitchen Electronic Appliance"),
    "toaster": ("E-Waste", "Electronic Appliance"),
    "clock": ("E-Waste", "Electronic Clock"),
    "backpack": ("Textile Waste", "Discarded Backpack / Fabric"),
    "handbag": ("Textile Waste", "Textile Handbag"),
    "tie": ("Textile Waste", "Textile Apparel"),
    "suitcase": ("Textile Waste", "Fabric Luggage"),
    "umbrella": ("Textile Waste", "Fabric Umbrella Remnant"),
    "chair": ("Mixed Waste", "Bulky Discarded Furniture"),
    "couch": ("Mixed Waste", "Bulky Upholstered Furniture"),
    "bed": ("Mixed Waste", "Bulky Mattress / Furniture"),
    "dining table": ("Mixed Waste", "Bulky Wood Waste"),
    "toilet": ("Mixed Waste", "Ceramic Sanitary Waste"),
    "sink": ("Mixed Waste", "Sanitary Basin Waste"),
    "refrigerator": ("Mixed Waste", "Major Bulky Appliance"),
    # Additional generic keywords
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


class ResNet50LocalEngine(BaseInferenceEngine):
    """
    Local ResNet50 Image Classification Engine using authoritative waste_resnet50.pth.
    Used for image uploads, citizen contributions, and single-object classification.
    """
    def __init__(self, weights_path: Optional[str] = None, version: str = "v2.1"):
        self.weights_path = weights_path or os.path.join(settings.MODELS_DIR, "waste_resnet50.pth")
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        super().__init__(version=version)

    def load_model(self):
        if not os.path.exists(self.weights_path):
            logger.warning(f"ResNet50 weights not found at {self.weights_path}. Model load deferred.")
            self.model = None
            self.is_loaded = False
            return

        try:
            sd = torch.load(self.weights_path, map_location=self.device, weights_only=True)
            out_features = 2
            if "fc.3.weight" in sd:
                out_features = sd["fc.3.weight"].shape[0]
            elif "fc.weight" in sd:
                out_features = sd["fc.weight"].shape[0]

            self.num_classes = out_features
            base_model = models.resnet50()

            if "fc.3.weight" in sd:
                base_model.fc = torch.nn.Sequential(
                    torch.nn.Linear(2048, 512),
                    torch.nn.ReLU(inplace=True),
                    torch.nn.Dropout(0.2),
                    torch.nn.Linear(512, out_features)
                )
            else:
                base_model.fc = torch.nn.Linear(2048, out_features)

            base_model.load_state_dict(sd, strict=True)
            base_model.to(self.device)
            base_model.eval()

            self.model = base_model
            self.is_loaded = True
            logger.info(f"Loaded ResNet50 from {self.weights_path} with {out_features} output classes.")
        except Exception as e:
            logger.error(f"Failed to load ResNet50 local model: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        t0 = time.time()
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "ResNet50 model not loaded"}

        try:
            tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1)[0]

            latency_ms = round((time.time() - t0) * 1000, 2)
            prob_list = probs.tolist()

            if getattr(self, "num_classes", 2) == 2:
                p0 = round(prob_list[0], 4)
                p1 = round(prob_list[1], 4)
                if p0 >= p1:
                    top_category = "Organic Waste"
                    detected_item = "Organic / Biodegradable Waste"
                    top_conf = p0
                else:
                    top_category = "Plastic"
                    detected_item = "Recyclable Solid Waste (Plastic / Packaging)"
                    top_conf = p1

                top_preds = [
                    {"category": "Organic Waste", "confidence": p0, "confidence_pct": int(p0 * 100)},
                    {"category": "Recyclable Solid Waste", "confidence": p1, "confidence_pct": int(p1 * 100)}
                ]
            else:
                top_k = min(3, len(prob_list))
                top_probs, top_indices = torch.topk(probs, k=top_k)
                top_idx = top_indices[0].item()
                top_category = MUNICIPAL_CATEGORIES[top_idx % len(MUNICIPAL_CATEGORIES)]
                top_conf = round(top_probs[0].item(), 4)
                detected_item = f"{top_category} Material"

                top_preds = []
                for p, idx in zip(top_probs.tolist(), top_indices.tolist()):
                    cat = MUNICIPAL_CATEGORIES[idx % len(MUNICIPAL_CATEGORIES)]
                    top_preds.append({
                        "category": cat,
                        "confidence": round(p, 4),
                        "confidence_pct": int(p * 100)
                    })

            return {
                "success": True,
                "task": "image_classification",
                "model_name": "ResNet50-WasteClassifier",
                "model_version": self.version,
                "framework": "PyTorch 2.2 / ResNet50",
                "predicted_category": top_category,
                "detected_item": detected_item,
                "confidence": top_conf,
                "confidence_pct": int(top_conf * 100),
                "top_predictions": top_preds,
                "bounding_box": [0.10, 0.10, 0.90, 0.90],
                "bbox_xywh": [0.10, 0.10, 0.80, 0.80],
                "color": CATEGORY_COLORS.get(top_category, "#3B82F6"),
                "latency_ms": latency_ms
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class YOLO11nLocalEngine(BaseInferenceEngine):
    """
    Local YOLO11n Object Detector using authoritative yolo11n.pt.
    Used for live camera frames, truck scanners, and real-time bounding box localization.
    """
    def __init__(self, weights_path: Optional[str] = None, version: str = "v2.1"):
        self.weights_path = weights_path or os.path.join(settings.MODELS_DIR, "yolo11n.pt")
        super().__init__(version=version)

    def load_model(self):
        if not os.path.exists(self.weights_path):
            logger.warning(f"YOLO11n weights not found at {self.weights_path}. Model load deferred.")
            self.model = None
            self.is_loaded = False
            return

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.weights_path)
            self.is_loaded = True
            logger.info(f"Loaded YOLO11n model from {self.weights_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO11n model: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, image: Image.Image, conf_threshold: float = 0.25) -> Dict[str, Any]:
        t0 = time.time()
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "YOLO11n model not loaded"}

        try:
            results = self.model(image, conf=conf_threshold, verbose=False)
            latency_ms = round((time.time() - t0) * 1000, 2)

            detections = []
            w, h = image.size

            for r in results:
                boxes = r.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    xyxy = box.xyxy[0].tolist()
                    xmin = round(max(0.0, min(1.0, xyxy[0] / max(1, w))), 4)
                    ymin = round(max(0.0, min(1.0, xyxy[1] / max(1, h))), 4)
                    xmax = round(max(0.0, min(1.0, xyxy[2] / max(1, w))), 4)
                    ymax = round(max(0.0, min(1.0, xyxy[3] / max(1, h))), 4)

                    conf = round(float(box.conf[0].item()), 4)
                    cls_id = int(box.cls[0].item())
                    raw_name = self.model.names.get(cls_id, "waste_object").lower()

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

            detections.sort(key=lambda d: d["confidence"], reverse=True)

            if detections:
                top = detections[0]
                top_cat = top["waste_category"]
                top_item = top["object_name"]
                top_conf = top["confidence"]
                top_bbox = top["bounding_box"]
                top_bbox_xywh = top["bbox_xywh"]
                top_color = top["color"]
            else:
                top_cat = "Mixed Waste"
                top_item = "Unclassified Waste Stream"
                top_conf = 0.30
                top_bbox = [0.10, 0.10, 0.90, 0.90]
                top_bbox_xywh = [0.10, 0.10, 0.80, 0.80]
                top_color = "#64748B"

            return {
                "success": True,
                "task": "object_detection",
                "model_name": "YOLO11n-WasteDetector",
                "model_version": self.version,
                "framework": "Ultralytics YOLO11",
                "predicted_category": top_cat,
                "detected_item": top_item,
                "confidence": top_conf,
                "confidence_pct": int(top_conf * 100),
                "bounding_box": top_bbox,
                "bbox_xywh": top_bbox_xywh,
                "color": top_color,
                "count": len(detections),
                "detections": detections,
                "latency_ms": latency_ms
            }
        except Exception as e:
            logger.error(f"YOLO11n predict error: {e}")
            return {"success": False, "error": str(e)}


class AIVisionService:
    """
    Centralized Municipal AI Vision Orchestrator.
    Manages task-aware routing (Uploads -> ResNet50, Frames -> YOLO11n),
    connects to standalone AI microservice or local neural weights,
    and invokes the classical CV fallback algorithm under documented failure conditions.
    """
    _active_resnet_engine: Optional[ResNet50LocalEngine] = None
    _active_yolo_engine: Optional[YOLO11nLocalEngine] = None
    _active_version: str = "v2.1"

    @classmethod
    def get_engines(cls) -> Tuple[ResNet50LocalEngine, YOLO11nLocalEngine]:
        if cls._active_resnet_engine is None:
            cls._active_resnet_engine = ResNet50LocalEngine(version=cls._active_version)
        if cls._active_yolo_engine is None:
            cls._active_yolo_engine = YOLO11nLocalEngine(version=cls._active_version)
        return cls._active_resnet_engine, cls._active_yolo_engine

    @classmethod
    def switch_active_model(cls, version: str, weights_path: Optional[str] = None) -> bool:
        """Atomically switches active inference model version."""
        try:
            cls._active_version = version
            if weights_path and "resnet" in weights_path.lower():
                cls._active_resnet_engine = ResNet50LocalEngine(weights_path=weights_path, version=version)
            elif weights_path and "yolo" in weights_path.lower():
                cls._active_yolo_engine = YOLO11nLocalEngine(weights_path=weights_path, version=version)
            else:
                cls._active_resnet_engine = ResNet50LocalEngine(version=version)
                cls._active_yolo_engine = YOLO11nLocalEngine(version=version)
            logger.info(f"Switched active AI Vision models to version {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch models to {version}: {e}")
            return False

    @staticmethod
    def calculate_image_hash(image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def calculate_blur_score(image: Image.Image) -> float:
        """Sharpness score using Laplacian gradient variance."""
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
        if width < 80 or height < 80:
            return False, "Image resolution too low (minimum 80x80 required)", 15.0

        if file_size_kb < 1.0:
            return False, "File size suspiciously small (<1KB)", 10.0

        if current_hash in existing_hashes:
            return False, "Duplicate image already exists in dataset", 50.0

        blur = AIVisionService.calculate_blur_score(image)
        if blur < 15.0:
            return False, f"Image appears excessively blurry (sharpness score {blur}/100)", blur

        return True, "Image passed quality validation pipeline", blur

    @staticmethod
    def extract_image_embedding(image: Image.Image) -> List[float]:
        """Dense 128-d normalized visual feature embedding vector for personal AI memory."""
        try:
            rgb_img = image.convert("RGB").resize((64, 64))
            arr = np.array(rgb_img, dtype=np.float32) / 255.0

            # 8x8 Grid Spatial Luminance (64 dims)
            grid_img = rgb_img.resize((8, 8), Image.Resampling.BOX)
            grid_arr = np.array(grid_img, dtype=np.float32) / 255.0
            luminance = (0.299 * grid_arr[:, :, 0] + 0.587 * grid_arr[:, :, 1] + 0.114 * grid_arr[:, :, 2]).flatten()

            # Quadrant Edge Gradients (32 dims)
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

            # Morphology (16 dims)
            w, h = image.size
            aspect_ratio = float(w) / float(max(1, h))
            morph_features = np.array([
                aspect_ratio, float(h) / float(max(1, w)),
                float(1.6 <= aspect_ratio <= 2.4), float(1.25 <= aspect_ratio <= 1.55),
                float(0.85 <= aspect_ratio <= 1.15), float(np.mean(arr)),
                float(np.std(arr)), float(np.mean(arr[:, :, 0])),
                float(np.mean(arr[:, :, 1])), float(np.mean(arr[:, :, 2])),
                float(np.max(arr) - np.min(arr)), float(np.median(arr)),
                float(len(arr[arr > 0.8]) / arr.size), float(len(arr[arr < 0.2]) / arr.size),
                float(np.var(arr[:, :, 0])), float(np.var(arr[:, :, 1]))
            ], dtype=np.float32)

            # Texture frequency bands (16 dims)
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
    def _run_primary_model(
        cls,
        image: Image.Image,
        task: str = "classification"
    ) -> Optional[Dict[str, Any]]:
        """
        Executes primary deep learning inference:
        - Image uploads -> ResNet50 (waste_resnet50.pth)
        - Camera frames -> YOLO11n (yolo11n.pt)
        Checks remote microservice if configured, else executes local PyTorch engine.
        """
        # 1. Try standalone AI microservice if configured
        from app.services.ai_client import AIServiceClient
        if AIServiceClient.is_configured():
            try:
                if task in ("detection", "detect", "frame"):
                    data = AIServiceClient.detect_frame(image)
                else:
                    data = AIServiceClient.classify_image(image)

                cat = data.get("predicted_category")
                conf = float(data.get("confidence", 0.0))
                if data and data.get("success", True) and cat and conf > 0.0:
                    return {
                        "predicted_category": cat,
                        "detected_item": data.get("detected_item") or f"{cat} Item",
                        "confidence": conf,
                        "confidence_pct": int(data.get("confidence_pct", conf * 100)),
                        "bounding_box": data.get("bounding_box", [0.10, 0.10, 0.90, 0.90]),
                        "bbox_xywh": data.get("bbox_xywh", [0.10, 0.10, 0.80, 0.80]),
                        "color": data.get("color", CATEGORY_COLORS.get(cat, "#3B82F6")),
                        "classification_method": data.get("classification_method") or f"remote_ai_service_{task}",
                        "latency_ms": data.get("latency_ms", 35.0),
                        "model_name": data.get("model_name", "Remote-AI-Service"),
                        "model_version": data.get("model_version", cls._active_version),
                        "model_framework": data.get("framework", "PyTorch 2.2"),
                        "detections": data.get("detections", []),
                        "top_predictions": data.get("top_predictions", []),
                        "fallback_used": data.get("fallback_used", False),
                        "requires_review": data.get("requires_review", False),
                        "fallback_reason": data.get("fallback_reason")
                    }
            except Exception as e:
                logger.warning(f"Remote AI microservice unavailable (using local fallback engine): {e}")

        # 2. Local Engine Execution
        resnet_engine, yolo_engine = cls.get_engines()

        if task in ("detection", "detect", "frame"):
            if yolo_engine and yolo_engine.is_loaded:
                res = yolo_engine.predict(image)
                if res.get("success"):
                    return {
                        "predicted_category": res.get("predicted_category"),
                        "detected_item": res.get("detected_item"),
                        "confidence": res.get("confidence", 0.0),
                        "confidence_pct": res.get("confidence_pct", 0),
                        "bounding_box": res.get("bounding_box", [0.10, 0.10, 0.90, 0.90]),
                        "bbox_xywh": res.get("bbox_xywh", [0.10, 0.10, 0.80, 0.80]),
                        "color": res.get("color", "#3B82F6"),
                        "classification_method": "yolo11n",
                        "model_name": "YOLO11n-WasteDetector",
                        "model_version": cls._active_version,
                        "model_framework": "Ultralytics YOLO11",
                        "latency_ms": res.get("latency_ms", 18.0),
                        "detections": res.get("detections", [])
                    }
        else:
            # Classification task -> ResNet50
            if resnet_engine and resnet_engine.is_loaded:
                res = resnet_engine.predict(image)
                if res.get("success"):
                    cat = res.get("predicted_category")
                    conf = res.get("confidence", 0.0)
                    return {
                        "predicted_category": cat,
                        "detected_item": res.get("detected_item"),
                        "confidence": conf,
                        "confidence_pct": int(conf * 100),
                        "bounding_box": [0.10, 0.10, 0.90, 0.90],
                        "bbox_xywh": [0.10, 0.10, 0.80, 0.80],
                        "color": CATEGORY_COLORS.get(cat, "#3B82F6"),
                        "classification_method": "resnet50",
                        "model_name": "ResNet50-WasteClassifier",
                        "model_version": cls._active_version,
                        "model_framework": "PyTorch 2.2 / ResNet50",
                        "latency_ms": res.get("latency_ms", 22.0),
                        "top_predictions": res.get("top_predictions", [])
                    }

        return None

    @classmethod
    def detect_and_classify(
        cls,
        image: Image.Image,
        filename_hint: str = "",
        task: str = "classification",
        force_fallback: bool = False,
        primary_should_fail: bool = False
    ) -> Dict[str, Any]:
        """
        Inference Orchestrator with Mandatory Fallback:
        1. Routes still images to ResNet50 and live frames to YOLO11n.
        2. If primary model succeeds with confidence >= threshold and valid category, returns primary result.
        3. If primary model fails, times out, raises exception, or yields low confidence:
           Activates classical CV multi-cue heuristic fallback algorithm!
        4. Distinguishes primary vs fallback in output metadata.
        """
        t0 = time.time()
        embedding = cls.extract_image_embedding(image)

        primary_status = "unavailable"
        primary_result = None

        # Determine task from filename or hints if not explicitly set
        fn = filename_hint.lower()
        if task == "classification" and any(k in fn for k in ["frame", "cam", "video", "truck"]):
            task = "detection"

        # Step 1: Attempt Primary Neural Model
        if not force_fallback and not primary_should_fail:
            try:
                prim = cls._run_primary_model(image, task=task)
                is_detection = task in ("detection", "detect", "frame")
                if prim and is_detection:
                    # Detection task: YOLO successfully analyzed frame
                    has_dets = bool(prim.get("detections"))
                    top_conf = prim.get("confidence", 0.0)
                    primary_status = "success"
                    primary_result = {
                        "predicted_category": prim.get("predicted_category", "No Objects Detected") if has_dets else "Empty Conveyor",
                        "detected_item": prim.get("detected_item", "Detected Object") if has_dets else "Clear Conveyor Stream",
                        "confidence": top_conf if has_dets else 0.95,
                        "confidence_pct": int(top_conf * 100) if has_dets else 95,
                        "bounding_box": prim.get("bounding_box", [0.10, 0.10, 0.90, 0.90]),
                        "bbox_xywh": prim.get("bbox_xywh", [0.10, 0.10, 0.80, 0.80]),
                        "color": prim.get("color", "#3B82F6"),
                        "classification_method": prim.get("classification_method", "yolo11n"),
                        "primary_model_status": "success",
                        "fallback_used": False,
                        "requires_review": False,
                        "latency_ms": prim.get("latency_ms", round((time.time() - t0) * 1000, 2)),
                        "model_name": prim.get("model_name", "YOLO11n-WasteDetector"),
                        "model_version": prim.get("model_version", cls._active_version),
                        "model_framework": prim.get("model_framework", "Ultralytics YOLO11"),
                        "detections": prim.get("detections", []),
                        "stage_notes": f"YOLO11n frame inference executed: {len(prim.get('detections', []))} detections",
                        "secondary_prediction": {
                            "predicted_category": "Mixed Waste",
                            "confidence": 0.20
                        }
                    }
                elif prim and prim.get("confidence", 0) >= settings.AI_CONFIDENCE_THRESHOLD and prim.get("predicted_category") in MUNICIPAL_CATEGORIES:
                    sec_cat = "Plastic" if prim["predicted_category"] == "Organic Waste" else "Organic Waste"
                    sec_conf = round(max(0.05, 1.0 - prim["confidence"]), 4)
                    if prim.get("top_predictions") and len(prim["top_predictions"]) > 1:
                        sec_cat = prim["top_predictions"][1].get("category", sec_cat)
                        sec_conf = prim["top_predictions"][1].get("confidence", sec_conf)

                    primary_status = "success"
                    primary_result = {
                        "predicted_category": prim["predicted_category"],
                        "detected_item": prim.get("detected_item", f"{prim['predicted_category']} Item"),
                        "confidence": prim["confidence"],
                        "confidence_pct": prim.get("confidence_pct", int(prim["confidence"] * 100)),
                        "bounding_box": prim.get("bounding_box", [0.10, 0.10, 0.90, 0.90]),
                        "bbox_xywh": prim.get("bbox_xywh", [0.10, 0.10, 0.80, 0.80]),
                        "color": prim.get("color", CATEGORY_COLORS.get(prim["predicted_category"], "#3B82F6")),
                        "classification_method": prim.get("classification_method", "primary_ai"),
                        "primary_model_status": "success",
                        "fallback_used": False,
                        "requires_review": False,
                        "latency_ms": prim.get("latency_ms", round((time.time() - t0) * 1000, 2)),
                        "model_name": prim.get("model_name", "ResNet50-WasteClassifier"),
                        "model_version": prim.get("model_version", cls._active_version),
                        "model_framework": prim.get("model_framework", "PyTorch 2.2"),
                        "stage_notes": f"Primary neural model ({prim.get('model_name', task)}) executed successfully",
                        "secondary_prediction": {
                            "predicted_category": sec_cat,
                            "confidence": sec_conf
                        }
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
                "embedding": embedding,
                "status": "High Confidence Detection",
                "is_low_confidence": False,
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            })
            return primary_result

        # Step 2: Primary Model Failed / Low Confidence -> Activate Fallback
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
                "bounding_box": [0.10, 0.10, 0.90, 0.90],
                "bbox_xywh": [0.10, 0.10, 0.80, 0.80],
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
            "model_name": "ClassicalCV-FallbackEngine",
            "embedding": embedding,
            "status": "Fallback Heuristic Classification" if not fallback_res.get("requires_review") else "Uncertain — Needs Verification",
            "is_low_confidence": fallback_res.get("requires_review", True)
        })

        return fallback_res

    @classmethod
    def classify_upload_image(cls, image: Image.Image, upload_id: Optional[int] = None) -> Dict[str, Any]:
        """Convenience method for image uploads (routes strictly to ResNet50 classification)."""
        res = cls.detect_and_classify(image, task="classification")
        is_fallback = res.get("fallback_used", False)
        conf = float(res.get("confidence", 0.0))
        req_rev = res.get("requires_review", False) or conf < 0.70 or is_fallback
        suitable = (not is_fallback) and (conf >= 0.70) and (not req_rev)
        
        return {
            "prediction_id": f"pred_cls_{int(time.time()*1000)}_{upload_id or 0}",
            "task": "classification",
            "model_id": res.get("model_name", "waste_resnet50"),
            "model_type": "fallback" if is_fallback else ("resnet50" if "resnet" in str(res.get("model_name", "")).lower() else "resnet50"),
            "predicted_class": res.get("predicted_category", "Unknown"),
            "confidence": conf,
            "class_scores": {
                res.get("predicted_category", "Unknown"): conf,
                "Other": round(max(0.0, 1.0 - conf), 4)
            },
            "bounding_box": res.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
            "fallback_used": is_fallback,
            "fallback_reason": res.get("fallback_details", {}).get("primary_status") or ("Confidence below threshold" if is_fallback else None),
            "suitable_for_automated_sorting": suitable,
            "requires_review": req_rev,
            "processing_time_ms": res.get("latency_ms", 25.0)
        }

    @classmethod
    def detect_camera_frame(cls, image: Image.Image, frame_id: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method for camera / conveyor / truck frames (routes to YOLO11n detection)."""
        res = cls.detect_and_classify(image, task="detection")
        is_fallback = res.get("fallback_used", False)
        conf = float(res.get("confidence", 0.0))
        detections = res.get("detections", [])
        req_rev = res.get("requires_review", False) or conf < 0.70 or is_fallback
        suitable = (not is_fallback) and (conf >= 0.70) and (not req_rev)

        return {
            "prediction_id": f"pred_det_{int(time.time()*1000)}_{frame_id or 'cam'}",
            "task": "detection",
            "model_id": res.get("model_name", "yolo11n"),
            "model_type": "fallback" if is_fallback else ("yolo11n" if "yolo" in str(res.get("model_name", "")).lower() else "yolo11n"),
            "predicted_class": res.get("predicted_category", "Unknown"),
            "confidence": conf,
            "detections": detections,
            "count": len(detections),
            "bounding_box": res.get("bounding_box", [0.1, 0.1, 0.9, 0.9]),
            "fallback_used": is_fallback,
            "fallback_reason": res.get("fallback_details", {}).get("primary_status") or ("Confidence below threshold" if is_fallback else None),
            "suitable_for_automated_sorting": suitable,
            "requires_review": req_rev,
            "processing_time_ms": res.get("latency_ms", 20.0)
        }

