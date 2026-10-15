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
    "unknown": "#94A3B8"        # Slate light
}

class AIFallbackService:
    """
    Mandatory Fallback Waste-Classification Algorithm.
    Independent classical computer vision and heuristic inference system
    triggered whenever primary deep learning models (YOLO / MobileNet / Decoupled AI)
    fail, time out, or produce invalid / low-confidence outputs.
    """

    @staticmethod
    def validate_and_preprocess(
        image_input: Union[Image.Image, np.ndarray, bytes]
    ) -> Tuple[bool, Optional[np.ndarray], Optional[str], Optional[str]]:
        """
        Layer 1: Image validation and preprocessing.
        Validates dimensions, channel format, corruption, extreme darkness, and severe blur.
        Returns (is_valid, rgb_numpy_array, error_code, error_message).
        """
        try:
            # 1. Convert input to RGB numpy array
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
                return False, None, "UNSUPPORTED_TYPE", "Unsupported image input type."

            h, w = img_rgb.shape[:2]

            # 2. Minimum resolution check
            if h < 32 or w < 32:
                return False, None, "RESOLUTION_TOO_LOW", f"Image resolution {w}x{h} is below minimum 32x32."

            # 3. Complete pitch black or pure white frame check
            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
            mean_brightness = float(np.mean(gray))
            std_dev = float(np.std(img_rgb))

            if std_dev == 0.0 and (mean_brightness < 5.0 or mean_brightness > 252.0):
                return False, None, "BLANK_FRAME", "Frame is completely blank and unusable."

            # 4. Blur check using Laplacian variance on scenes with sufficient contrast
            gray_std = float(np.std(gray))
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if lap_var < 1.0 and (w >= 100 and h >= 100) and gray_std >= 15.0:
                return False, None, "IMAGE_TOO_BLURRY", f"Image is excessively blurred (sharpness {lap_var:.1f})."

            # Resize to standardized processing dimensions if excessively large to save CPU
            if max(h, w) > 1024:
                scale = 1024.0 / max(h, w)
                img_rgb = cv2.resize(img_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            return True, img_rgb, None, None

        except Exception as e:
            logger.error(f"Fallback validation error: {e}")
            return False, None, "PROCESSING_ERROR", str(e)

    @staticmethod
    def extract_classical_features(img_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Layer 2: Classical Computer Vision Feature Extraction.
        Computes HSV/Lab color distributions, edge density, contour geometry, and texture variance.
        """
        h, w = img_rgb.shape[:2]
        total_pixels = h * w

        # 1. Color Space Representations
        img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2Lab)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

        # HSV Channels: H [0, 179], S [0, 255], V [0, 255]
        h_channel = img_hsv[:, :, 0]
        s_channel = img_hsv[:, :, 1]
        v_channel = img_hsv[:, :, 2]

        # Color fractions
        green_mask = cv2.inRange(img_hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
        blue_mask = cv2.inRange(img_hsv, np.array([90, 50, 40]), np.array([135, 255, 255]))
        yellow_mask = cv2.inRange(img_hsv, np.array([20, 50, 80]), np.array([35, 255, 255]))
        brown_cardboard_mask = cv2.inRange(img_hsv, np.array([10, 30, 40]), np.array([25, 200, 200]))
        red_mask_1 = cv2.inRange(img_hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        red_mask_2 = cv2.inRange(img_hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)

        green_ratio = float(np.count_nonzero(green_mask)) / total_pixels
        blue_ratio = float(np.count_nonzero(blue_mask)) / total_pixels
        yellow_ratio = float(np.count_nonzero(yellow_mask)) / total_pixels
        brown_ratio = float(np.count_nonzero(brown_cardboard_mask)) / total_pixels
        red_ratio = float(np.count_nonzero(red_mask)) / total_pixels

        mean_saturation = float(np.mean(s_channel))
        mean_value = float(np.mean(v_channel))
        saturation_var = float(np.var(s_channel))

        # 2. Edge and Contour Features
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / total_pixels

        # Contours for shape geometry
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_area = 0.0
        aspect_ratio = 1.0
        bounding_box = [0.10, 0.10, 0.90, 0.90] # default normalized [ymin, xmin, ymax, xmax]
        circularity = 0.0
        rectangularity = 0.0

        if contours:
            largest_c = max(contours, key=cv2.contourArea)
            largest_area = float(cv2.contourArea(largest_c))
            perimeter = float(cv2.arcLength(largest_c, True))
            bx, by, bw, bh = cv2.boundingRect(largest_c)
            if bh > 0 and bw > 0:
                aspect_ratio = float(bw) / float(bh)
                rect_area = bw * bh
                rectangularity = float(largest_area / rect_area) if rect_area > 0 else 0.0
                bounding_box = [
                    round(max(0.0, min(1.0, by / h)), 4),
                    round(max(0.0, min(1.0, bx / w)), 4),
                    round(max(0.0, min(1.0, (by + bh) / h)), 4),
                    round(max(0.0, min(1.0, (bx + bw) / w)), 4)
                ]
            if perimeter > 0:
                circularity = float(4.0 * np.pi * largest_area / (perimeter * perimeter))

        # 3. Specular Reflection (Indicators of Glass, Metal, or Glossy Plastic)
        specular_mask = cv2.inRange(img_hsv, np.array([0, 0, 240]), np.array([180, 40, 255]))
        specular_ratio = float(np.count_nonzero(specular_mask)) / total_pixels

        # 4. Texture Variance (Laplacian of Gaussian / Gradient Energy)
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
        Layers 3, 4, 5: Heuristic rule-based fallback classification.
        Evaluates visual feature evidence across canonical categories and assigns
        transparent heuristic scores and review requirements.
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
                "detected_item": "Invalid Image Input",
                "confidence": 0.0,
                "heuristic_score": 0.0,
                "requires_review": True,
                "bounding_box": [0.1, 0.1, 0.9, 0.9],
                "bbox_xywh": [0.1, 0.1, 0.8, 0.8],
                "color": "#94A3B8",
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }

        features = cls.extract_classical_features(img_rgb)
        scores: Dict[str, float] = {cat: 0.10 for cat in MUNICIPAL_CATEGORIES}
        subitem_names: Dict[str, str] = {cat: f"{cat} Item" for cat in MUNICIPAL_CATEGORIES}

        # Rule Set 1: Organic / Food Waste
        # Strong green or yellow-green vegetative coloration with irregular organic contours
        if features["green_ratio"] > 0.18 or (features["green_ratio"] > 0.08 and features["yellow_ratio"] > 0.10):
            scores["Organic Waste"] += 0.50 + min(0.30, features["green_ratio"] * 0.8)
            subitem_names["Organic Waste"] = "Vegetative Organic Plant / Garden Waste"
        if features["yellow_ratio"] > 0.22 and features["green_ratio"] > 0.05:
            scores["Food Waste"] += 0.45 + min(0.30, features["yellow_ratio"] * 0.7)
            subitem_names["Food Waste"] = "Food Waste / Kitchen Scraps"

        # Rule Set 2: Cardboard & Packaging Paper
        # Earthy brown hue, matte finish, rectangular edges
        if features["brown_ratio"] > 0.20:
            scores["Cardboard"] += 0.55 + min(0.25, features["brown_ratio"] * 0.6)
            subitem_names["Cardboard"] = "Corrugated Cardboard Box / Sheet"
        elif features["mean_value"] > 180 and features["mean_saturation"] < 40 and features["edge_density"] > 0.04:
            scores["Paper"] += 0.50 + min(0.25, features["edge_density"] * 2.0)
            subitem_names["Paper"] = "Clean White / Office Paper"

        # Rule Set 3: Plastic Containers & Bottles
        # Blue/cyan packaging spectrum or cylindrical / bottle-like aspect ratio with specular highlights
        if features["blue_ratio"] > 0.15:
            scores["Plastic"] += 0.45 + min(0.30, features["blue_ratio"] * 0.8)
            subitem_names["Plastic"] = "Rigid / Flexible Blue Plastic Packaging"
        if (0.35 <= features["aspect_ratio"] <= 0.65 or 1.5 <= features["aspect_ratio"] <= 2.8) and features["specular_ratio"] > 0.015:
            scores["Plastic"] += 0.25
            subitem_names["Plastic"] = "PET Plastic Bottle / Container"

        # Rule Set 4: Glass Bottles & Jars
        # High specular reflection + high transparency/brightness + circular/cylindrical symmetry
        if features["specular_ratio"] > 0.035 and features["circularity"] > 0.25:
            scores["Glass"] += 0.45 + min(0.30, features["specular_ratio"] * 4.0)
            subitem_names["Glass"] = "Glass Beverage Bottle / Jar"

        # Rule Set 5: Metal Cans & Scrap
        # Low saturation, high specular highlights, reflective metallic sheen
        if features["mean_saturation"] < 45 and features["specular_ratio"] > 0.030 and features["gradient_energy"] > 250:
            scores["Metal"] += 0.45 + min(0.25, features["specular_ratio"] * 3.5)
            subitem_names["Metal"] = "Aluminum Can / Scrap Metal"

        # Rule Set 6: E-Waste
        # Dark rectangular silhouette (mobile phone / battery form factor 1.8-2.3) or dense PCB circuitry edges
        ar = features["aspect_ratio"]
        if (1.75 <= ar <= 2.35 or 0.42 <= ar <= 0.58) and features["rectangularity"] > 0.60:
            scores["E-Waste"] += 0.40
            subitem_names["E-Waste"] = "Mobile Phone / Electronic Device"
        if features["edge_density"] > 0.12 and features["green_ratio"] > 0.10: # Green PCB board
            scores["E-Waste"] += 0.45
            subitem_names["E-Waste"] = "Electronic Circuit Board / PCB"

        # Rule Set 7: Hazardous Waste
        # Red warning canisters / syringes / biohazard flags
        if features["red_ratio"] > 0.20:
            scores["Hazardous Waste"] += 0.45 + min(0.30, features["red_ratio"] * 0.8)
            subitem_names["Hazardous Waste"] = "Hazardous Waste Canister / Chemical Container"

        # Rule Set 8: Filename semantic hint reinforcement if available
        fn = filename_hint.lower()
        if fn:
            keyword_mappings = {
                "phone": ("E-Waste", "Mobile Phone / Smartphone", 0.40),
                "mobile": ("E-Waste", "Mobile Phone / Smartphone", 0.40),
                "battery": ("E-Waste", "Battery / Cell", 0.40),
                "laptop": ("E-Waste", "Laptop / Computer", 0.40),
                "plastic": ("Plastic", "Plastic Container / Bottle", 0.35),
                "bottle": ("Plastic", "Plastic Bottle (PET)", 0.35),
                "cardboard": ("Cardboard", "Cardboard Box", 0.35),
                "box": ("Cardboard", "Cardboard Packaging", 0.30),
                "paper": ("Paper", "Paper / Newspaper", 0.35),
                "glass": ("Glass", "Glass Bottle / Jar", 0.35),
                "can": ("Metal", "Aluminum Can", 0.35),
                "metal": ("Metal", "Scrap Metal", 0.35),
                "organic": ("Organic Waste", "Organic Waste", 0.35),
                "leaf": ("Organic Waste", "Garden Plant / Leaf Waste", 0.40),
                "food": ("Food Waste", "Food Waste Leftovers", 0.40),
                "syringe": ("Hazardous Waste", "Medical Waste / Syringe", 0.45)
            }
            for kw, (hint_cat, hint_item, boost) in keyword_mappings.items():
                if kw in fn:
                    scores[hint_cat] += boost
                    subitem_names[hint_cat] = hint_item
                    break

        # Sort candidate categories by heuristic score
        sorted_candidates = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_category, top_raw_score = sorted_candidates[0]

        # Bound score between 0.20 and 0.92 (never claim 100% certainty for heuristics)
        calibrated_score = round(min(0.92, max(0.20, top_raw_score)), 4)
        ymin, xmin, ymax, xmax = features["bounding_box"]
        bbox_xywh = [xmin, ymin, round(xmax - xmin, 4), round(ymax - ymin, 4)]
        latency_ms = round((time.time() - t0) * 1000, 2)

        # Layer 5: Unknown and Manual Review Handling
        # If confidence is below 0.38, classify honestly as 'unknown' and flag for manual review
        if calibrated_score < 0.38:
            predicted_category = "unknown"
            detected_item = "Uncertain Waste Material"
            requires_review = True
            color = "#94A3B8"
        else:
            predicted_category = top_category
            detected_item = subitem_names.get(top_category, f"{top_category} Item")
            requires_review = (calibrated_score < settings.AI_CONFIDENCE_THRESHOLD)
            color = CATEGORY_COLORS.get(predicted_category, "#3B82F6")

        return {
            "success": True,
            "predicted_category": predicted_category,
            "detected_item": detected_item,
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
            "latency_ms": latency_ms,
            "features_summary": {
                "aspect_ratio": round(features["aspect_ratio"], 2),
                "edge_density": round(features["edge_density"], 4),
                "specular_ratio": round(features["specular_ratio"], 4),
                "green_ratio": round(features["green_ratio"], 3),
                "brown_ratio": round(features["brown_ratio"], 3),
                "blue_ratio": round(features["blue_ratio"], 3)
            },
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "stage_notes": "Classical Computer Vision Heuristic Fallback Analysis"
        }

    @classmethod
    def classify_image(cls, image: Union[Image.Image, np.ndarray, bytes], filename_hint: str = "") -> Dict[str, Any]:
        """Classifies a static uploaded image using classical computer vision fallback."""
        return cls.classify_with_fallback(image, filename_hint=filename_hint)

    @classmethod
    def classify_frame(cls, frame: Union[Image.Image, np.ndarray, bytes], filename_hint: str = "") -> Dict[str, Any]:
        """Classifies a real-time video/webcam frame using classical computer vision fallback."""
        return cls.classify_with_fallback(frame, filename_hint=filename_hint)
