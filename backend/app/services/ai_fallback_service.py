import io
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List, Union
from PIL import Image, ImageStat
import numpy as np
import cv2

from app.core.config import settings

logger = logging.getLogger("wastedash.ai_fallback")

# The 11 Canonical Greater Chennai Corporation Municipal Waste Categories
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

CATEGORY_COLORS = {
    "Organic Waste": "#10B981", # Emerald
    "Food Waste": "#059669",    # Dark Emerald
    "Plastic": "#3B82F6",       # Blue
    "Paper": "#EAB308",         # Yellow
    "Cardboard": "#D97706",     # Ochre
    "Glass": "#F59E0B",         # Amber
    "Metal": "#64748B",         # Slate
    "Textile Waste": "#EC4899", # Pink
    "E-Waste": "#8B5CF6",       # Purple
    "Hazardous Waste": "#EF4444",# Red
    "Mixed Waste": "#64748B",   # Gray
    "unknown": "#94A3B8"        # Slate light
}


class AIFallbackService:
    """
    Repaired Classical Computer Vision & Heuristic Fallback Engine.
    Executes multi-cue classical vision analysis (HSV color distribution,
    contour geometry, aspect ratio, specular reflection, and edge variance)
    whenever primary neural models (ResNet50 / YOLO11n / Remote Microservice)
    fail, time out, encounter errors, or yield confidence below the municipal threshold.
    """

    @staticmethod
    def validate_and_preprocess(
        image_input: Union[Image.Image, np.ndarray, bytes]
    ) -> Tuple[bool, Optional[np.ndarray], Optional[str], Optional[str]]:
        """
        Layer 1: Input Validation and Normalization.
        Validates dimensions, channels, corruption, darkness, and excessive blur.
        Returns: (is_valid, rgb_numpy_array, error_code, error_message).
        """
        try:
            if isinstance(image_input, bytes):
                if len(image_input) == 0:
                    return False, None, "EMPTY_PAYLOAD", "Input image payload is empty."
                if len(image_input) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    return False, None, "PAYLOAD_TOO_LARGE", f"Image exceeds {settings.MAX_IMAGE_SIZE_MB}MB limit."
                nparr = np.frombuffer(image_input, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    return False, None, "CORRUPTED_IMAGE", "Could not decode image from byte payload."
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            elif isinstance(image_input, Image.Image):
                img_rgb = np.array(image_input.convert("RGB"))
            elif isinstance(image_input, np.ndarray):
                if len(image_input.shape) == 2:
                    img_rgb = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
                elif image_input.shape[2] == 4:
                    img_rgb = cv2.cvtColor(image_input, cv2.COLOR_RGBA2RGB)
                else:
                    img_rgb = image_input.copy()
            else:
                return False, None, "UNSUPPORTED_TYPE", f"Unsupported image input type {type(image_input)}."

            h, w = img_rgb.shape[:2]

            # Minimum resolution check
            if h < 32 or w < 32:
                return False, None, "RESOLUTION_TOO_LOW", f"Image resolution {w}x{h} is below minimum 32x32."

            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
            mean_brightness = float(np.mean(gray))
            std_dev = float(np.std(img_rgb))

            # Blank or solid pitch-black/pure-white check
            if std_dev < 1.0 and (mean_brightness < 8.0 or mean_brightness > 248.0):
                return False, None, "BLANK_FRAME", "Frame is completely blank or underexposed."

            # Severe blur check
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if lap_var < 0.5 and (w >= 100 and h >= 100) and float(np.std(gray)) >= 20.0:
                return False, None, "IMAGE_TOO_BLURRY", f"Image is excessively blurred (sharpness {lap_var:.1f})."

            # Scale down large images for CPU efficiency
            if max(h, w) > 1024:
                scale = 1024.0 / max(h, w)
                img_rgb = cv2.resize(img_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            return True, img_rgb, None, None

        except Exception as e:
            logger.error(f"Fallback preprocessing exception: {e}")
            return False, None, "PROCESSING_ERROR", str(e)

    @staticmethod
    def extract_classical_features(img_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Layer 2: Multi-Cue Classical Computer Vision Feature Extraction.
        """
        h, w = img_rgb.shape[:2]
        total_pixels = float(max(1, h * w))

        # Color Space Representations
        img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

        h_channel = img_hsv[:, :, 0]
        s_channel = img_hsv[:, :, 1]
        v_channel = img_hsv[:, :, 2]

        mean_saturation = float(np.mean(s_channel))
        mean_value = float(np.mean(v_channel))
        saturation_var = float(np.var(s_channel))

        # Distinct color mask ratios
        green_mask = cv2.inRange(img_hsv, np.array([32, 35, 35]), np.array([88, 255, 255]))
        blue_mask = cv2.inRange(img_hsv, np.array([88, 40, 40]), np.array([135, 255, 255]))
        yellow_mask = cv2.inRange(img_hsv, np.array([18, 40, 70]), np.array([34, 255, 255]))
        brown_mask = cv2.inRange(img_hsv, np.array([8, 25, 30]), np.array([24, 210, 210]))
        red1 = cv2.inRange(img_hsv, np.array([0, 60, 40]), np.array([10, 255, 255]))
        red2 = cv2.inRange(img_hsv, np.array([170, 60, 40]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red1, red2)

        green_ratio = float(np.count_nonzero(green_mask)) / total_pixels
        blue_ratio = float(np.count_nonzero(blue_mask)) / total_pixels
        yellow_ratio = float(np.count_nonzero(yellow_mask)) / total_pixels
        brown_ratio = float(np.count_nonzero(brown_mask)) / total_pixels
        red_ratio = float(np.count_nonzero(red_mask)) / total_pixels

        # Specular reflection highlights (glossy plastic, polished metal, glass)
        specular_mask = cv2.inRange(img_hsv, np.array([0, 0, 220]), np.array([180, 45, 255]))
        specular_ratio = float(np.count_nonzero(specular_mask)) / total_pixels

        # Edge analysis
        edges = cv2.Canny(gray, 40, 140)
        edge_density = float(np.count_nonzero(edges)) / total_pixels

        # Contours & Shape geometry
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_area = 0.0
        aspect_ratio = 1.0
        rectangularity = 0.0
        circularity = 0.0
        bounding_box = [0.10, 0.10, 0.90, 0.90]

        if contours:
            largest_c = max(contours, key=cv2.contourArea)
            largest_area = float(cv2.contourArea(largest_c))
            perimeter = float(cv2.arcLength(largest_c, True))
            bx, by, bw, bh = cv2.boundingRect(largest_c)
            if bh > 0 and bw > 0:
                aspect_ratio = float(bw) / float(bh)
                rect_area = float(bw * bh)
                rectangularity = float(largest_area / rect_area) if rect_area > 0 else 0.0
                bounding_box = [
                    round(max(0.0, min(1.0, by / h)), 4),
                    round(max(0.0, min(1.0, bx / w)), 4),
                    round(max(0.0, min(1.0, (by + bh) / h)), 4),
                    round(max(0.0, min(1.0, (bx + bw) / w)), 4)
                ]
            if perimeter > 0:
                circularity = float(4.0 * np.pi * largest_area / (perimeter * perimeter))

        # Texture gradient energy
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_energy = float(np.mean(sobelx**2 + sobely**2))

        return {
            "green_ratio": green_ratio,
            "blue_ratio": blue_ratio,
            "yellow_ratio": yellow_ratio,
            "brown_ratio": brown_ratio,
            "red_ratio": red_ratio,
            "mean_saturation": mean_saturation,
            "mean_value": mean_value,
            "saturation_var": saturation_var,
            "edge_density": edge_density,
            "largest_contour_fraction": largest_area / total_pixels,
            "aspect_ratio": aspect_ratio,
            "rectangularity": rectangularity,
            "circularity": circularity,
            "specular_ratio": specular_ratio,
            "gradient_energy": gradient_energy,
            "bounding_box": bounding_box
        }

    @classmethod
    def classify_with_fallback(
        cls,
        image_input: Union[Image.Image, np.ndarray, bytes],
        filename_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates visual evidence and assigns calibrated heuristic scores.
        Handles blank, corrupt, or unrecognizable frames safely as 'unknown' + 'requires_review'.
        """
        t0 = time.time()
        is_valid, img_rgb, err_code, err_msg = cls.validate_and_preprocess(image_input)
        if not is_valid:
            return {
                "success": False,
                "error_code": err_code,
                "error_message": err_msg,
                "classification_method": "fallback_validation_rejected",
                "fallback_used": True,
                "predicted_category": "unknown",
                "detected_item": "Unclassified / Corrupted Input",
                "confidence": 0.0,
                "confidence_pct": 0,
                "heuristic_score": 0.0,
                "requires_review": True,
                "bounding_box": [0.10, 0.10, 0.90, 0.90],
                "bbox_xywh": [0.10, 0.10, 0.80, 0.80],
                "color": "#94A3B8",
                "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                "stage_notes": f"Fallback input rejected: {err_msg}"
            }

        features = cls.extract_classical_features(img_rgb)
        scores: Dict[str, float] = {cat: 0.15 for cat in MUNICIPAL_CATEGORIES}
        subitem_names: Dict[str, str] = {cat: f"{cat} Material" for cat in MUNICIPAL_CATEGORIES}

        # Multi-cue evidence rules
        # 1. Organic Waste (leaves, trimmings, coconut husks)
        if features["green_ratio"] > 0.08:
            scores["Organic Waste"] += 0.40 + min(0.35, features["green_ratio"] * 0.9)
            subitem_names["Organic Waste"] = "Vegetative Organic Plant / Leaf Waste"

        # 2. Food Waste (kitchen wet scraps, yellow/orange peels, food plate leftovers)
        if features["yellow_ratio"] > 0.12 or (features["green_ratio"] > 0.04 and features["yellow_ratio"] > 0.06):
            scores["Food Waste"] += 0.38 + min(0.32, (features["yellow_ratio"] + features["green_ratio"]) * 0.7)
            subitem_names["Food Waste"] = "Food Waste Leftovers / Peels"

        # 3. Cardboard & Shipping Packaging (warm brown, kraft cardboard, box aspect)
        if features["brown_ratio"] > 0.10:
            scores["Cardboard"] += 0.48 + min(0.30, features["brown_ratio"] * 0.8)
            subitem_names["Cardboard"] = "Corrugated Cardboard Box / Shipping Carton"

        # 4. Clean Paper (high brightness, low saturation, moderate edge density)
        if features["mean_value"] > 160 and features["mean_saturation"] < 50:
            scores["Paper"] += 0.42 + min(0.25, features["edge_density"] * 1.5)
            subitem_names["Paper"] = "Clean Paper / Newspaper / Office Paper"

        # 5. Plastic (blue packaging, specular sheen, cylindrical / bottle aspect)
        if features["blue_ratio"] > 0.10:
            scores["Plastic"] += 0.45 + min(0.30, features["blue_ratio"] * 0.8)
            subitem_names["Plastic"] = "Rigid / Flexible Blue Plastic Packaging"
        ar = features["aspect_ratio"]
        if (0.30 <= ar <= 0.70 or 1.45 <= ar <= 3.1) and features["specular_ratio"] > 0.005:
            scores["Plastic"] += 0.30
            subitem_names["Plastic"] = "PET Plastic Bottle / Plastic Container"

        # 6. Glass (specular highlights + high circularity / cylindrical contour)
        if features["specular_ratio"] > 0.012 and (features["circularity"] > 0.18 or 0.35 <= ar <= 0.65):
            scores["Glass"] += 0.40 + min(0.25, features["specular_ratio"] * 5.0)
            subitem_names["Glass"] = "Glass Beverage Bottle / Jar"

        # 7. Metal (low saturation, metallic sheen, high gradient energy)
        if features["mean_saturation"] < 55 and features["specular_ratio"] > 0.008 and features["gradient_energy"] > 100:
            scores["Metal"] += 0.42 + min(0.25, features["specular_ratio"] * 4.0)
            subitem_names["Metal"] = "Aluminum Can / Scrap Metal"

        # 8. E-Waste (phone/tablet form factor 1.6-2.4, dark rectangular body or dense PCB edge density)
        if (1.6 <= ar <= 2.4 or 0.42 <= ar <= 0.62) and features["rectangularity"] > 0.45:
            scores["E-Waste"] += 0.38
            subitem_names["E-Waste"] = "Mobile Phone / Electronic Device"
        if features["edge_density"] > 0.09 and features["green_ratio"] > 0.06:
            scores["E-Waste"] += 0.42
            subitem_names["E-Waste"] = "Electronic Circuit Board (PCB)"

        # 9. Hazardous Waste (red warning color or chemical container)
        if features["red_ratio"] > 0.12:
            scores["Hazardous Waste"] += 0.45 + min(0.30, features["red_ratio"] * 0.8)
            subitem_names["Hazardous Waste"] = "Hazardous Waste Container / Medical Item"

        # 10. Filename semantic hint reinforcement if provided
        fn = (filename_hint or "").lower()
        if fn:
            keywords = {
                "phone": ("E-Waste", "Mobile Phone / Smartphone", 0.42),
                "mobile": ("E-Waste", "Mobile Phone / Smartphone", 0.42),
                "battery": ("E-Waste", "Battery / Cell", 0.42),
                "laptop": ("E-Waste", "Laptop Computer", 0.42),
                "plastic": ("Plastic", "Plastic Bottle / Container", 0.38),
                "bottle": ("Plastic", "Plastic Bottle (PET)", 0.38),
                "cardboard": ("Cardboard", "Corrugated Cardboard Box", 0.38),
                "box": ("Cardboard", "Cardboard Packaging", 0.35),
                "paper": ("Paper", "Clean Paper", 0.38),
                "glass": ("Glass", "Glass Bottle / Jar", 0.38),
                "can": ("Metal", "Aluminum Beverage Can", 0.38),
                "metal": ("Metal", "Scrap Metal / Can", 0.38),
                "organic": ("Organic Waste", "Organic Garden Waste", 0.40),
                "leaf": ("Organic Waste", "Garden Plant / Leaf Waste", 0.42),
                "food": ("Food Waste", "Food Waste Leftovers", 0.42),
                "syringe": ("Hazardous Waste", "Medical Waste / Syringe", 0.45)
            }
            for kw, (hint_cat, hint_item, boost) in keywords.items():
                if kw in fn:
                    scores[hint_cat] += boost
                    subitem_names[hint_cat] = hint_item
                    break

        # Sort candidate categories by score
        sorted_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_cat, top_raw_score = sorted_scores[0]
        second_cat, second_raw_score = sorted_scores[1]

        # Calibrate score between 0.20 and 0.88
        calibrated_score = round(min(0.88, max(0.20, top_raw_score)), 4)
        ymin, xmin, ymax, xmax = features["bounding_box"]
        bbox_xywh = [xmin, ymin, round(xmax - xmin, 4), round(ymax - ymin, 4)]
        latency_ms = round((time.time() - t0) * 1000, 2)

        # Unknown / Manual review threshold: < 0.32
        if calibrated_score < 0.32:
            pred_cat = "unknown"
            item_name = "Uncertain Waste Material"
            requires_review = True
            color = "#94A3B8"
        else:
            pred_cat = top_cat
            item_name = subitem_names.get(top_cat, f"{top_cat} Item")
            requires_review = (calibrated_score < settings.AI_CONFIDENCE_THRESHOLD)
            color = CATEGORY_COLORS.get(pred_cat, "#3B82F6")

        weight_map = {
            "E-Waste": 0.25, "Plastic": 0.08, "Paper": 0.05, "Cardboard": 0.35,
            "Glass": 0.45, "Metal": 0.15, "Organic Waste": 0.60, "Food Waste": 0.50,
            "Textile Waste": 0.30, "Hazardous Waste": 0.20, "Mixed Waste": 0.40,
            "unknown": 0.25
        }

        return {
            "success": True,
            "predicted_category": pred_cat,
            "detected_item": item_name,
            "confidence": calibrated_score,
            "confidence_pct": int(calibrated_score * 100),
            "heuristic_score": calibrated_score,
            "classification_method": "fallback_heuristic",
            "fallback_used": True,
            "primary_model_status": "fallback_activated",
            "requires_review": requires_review,
            "bounding_box": [ymin, xmin, ymax, xmax],
            "bbox_xywh": bbox_xywh,
            "color": color,
            "estimated_weight_kg": weight_map.get(pred_cat, 0.30),
            "latency_ms": latency_ms,
            "secondary_prediction": {
                "predicted_category": second_cat,
                "confidence": round(min(0.70, second_raw_score), 3)
            },
            "features_summary": {
                "aspect_ratio": round(features["aspect_ratio"], 2),
                "edge_density": round(features["edge_density"], 4),
                "specular_ratio": round(features["specular_ratio"], 4),
                "green_ratio": round(features["green_ratio"], 3),
                "brown_ratio": round(features["brown_ratio"], 3),
                "blue_ratio": round(features["blue_ratio"], 3)
            },
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "stage_notes": "Classical Computer Vision Multi-Cue Heuristic Fallback Analysis"
        }

    @classmethod
    def classify_image(cls, image: Union[Image.Image, np.ndarray, bytes], filename_hint: str = "") -> Dict[str, Any]:
        return cls.classify_with_fallback(image, filename_hint=filename_hint)

    @classmethod
    def classify_frame(cls, frame: Union[Image.Image, np.ndarray, bytes], filename_hint: str = "") -> Dict[str, Any]:
        return cls.classify_with_fallback(frame, filename_hint=filename_hint)
