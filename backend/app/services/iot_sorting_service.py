import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.iot import IoTSortingRecord

logger = logging.getLogger("wastedash.iot_sorting")

# -------------------------------------------------------------------------
# BIN CONFIGURATION & CATEGORY MAPPING
# -------------------------------------------------------------------------
# Bin 1: Organic / Wet / Compostable
# Bin 2: Recyclables (Plastic, Paper, Glass, Metals)
# Bin 3: High-Value Scrap & Electronic Waste
# Bin 4: Reject / Manual Review Chute (Low Confidence, Ambiguous, Fallback)

BIN_DEFINITIONS = {
    1: {"name": "bin_1_organic", "label": "Organic & Wet Waste", "chute": "Conveyor Chute A"},
    2: {"name": "bin_2_recyclables", "label": "Dry Recyclables (Plastic/Paper/Metal)", "chute": "Pneumatic Arm B"},
    3: {"name": "bin_3_scrap_ewaste", "label": "High-Value Scrap & E-Waste", "chute": "Robotic Diverter C"},
    4: {"name": "bin_4_reject_chute", "label": "Reject & Manual Review Chute", "chute": "Fail-Safe Direct Drop"},
}

CATEGORY_TO_BIN = {
    # Organic / Wet
    "organic waste": 1,
    "organic": 1,
    "food waste": 1,
    "wet waste": 1,
    "biodegradable": 1,
    "banana": 1,
    "apple": 1,
    "sandwich": 1,
    "orange": 1,
    "broccoli": 1,
    "carrot": 1,
    "pizza": 1,
    "donut": 1,
    "cake": 1,
    "potted plant": 1,

    # Recyclable / Dry
    "recyclable waste": 2,
    "recyclable": 2,
    "plastic": 2,
    "plastic waste": 2,
    "bottle": 2,
    "can": 2,
    "cup": 2,
    "paper": 2,
    "cardboard": 2,
    "glass": 2,
    "book": 2,
    "wine glass": 2,
    "fork": 2,
    "knife": 2,
    "spoon": 2,
    "bowl": 2,

    # E-Waste / High-Value Scrap
    "e-waste": 3,
    "ewaste": 3,
    "electronic waste": 3,
    "cell phone": 3,
    "laptop": 3,
    "mouse": 3,
    "remote": 3,
    "keyboard": 3,
    "microwave": 3,
    "oven": 3,
    "toaster": 3,
    "tv": 3,
    "clock": 3,
    "metal scrap": 3,
    "hazardous": 3,
}

CONFIDENCE_SAFETY_THRESHOLD = 0.70


class BaseSortingAdapter:
    """Abstract interface for physical sorting actuators."""
    def dispatch(self, bin_index: int, item_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_physical_placement(self, bin_index: int, item_id: str) -> Tuple[bool, str]:
        raise NotImplementedError


class SimulatedSortingAdapter(BaseSortingAdapter):
    """
    Deterministic simulated diverter with break-beam optical sensor confirmation.
    Simulates ~35-50ms pneumatic actuator latency.
    """
    def dispatch(self, bin_index: int, item_id: str) -> Dict[str, Any]:
        t0 = time.time()
        # Simulated fast pneumatic valve response
        latency_ms = round(35.0 + (hash(item_id) % 15), 1)
        return {
            "actuator_id": f"PNEUMATIC_ARM_0{bin_index}" if bin_index in (1, 2, 3) else "FAILSAFE_GRAVITY_CHUTE",
            "latency_ms": latency_ms,
            "signal": "HIGH",
            "timestamp": datetime.utcnow().isoformat()
        }

    def verify_physical_placement(self, bin_index: int, item_id: str) -> Tuple[bool, str]:
        # Optical break-beam sensor at chute entrance confirms arrival
        target_name = BIN_DEFINITIONS.get(bin_index, {}).get("name", "bin_4_reject_chute")
        return True, target_name


class IoTSortingSafetyService:
    """
    Authoritative safety and orchestration service for physical conveyor sorting actuators.
    Guarantees:
      1. Emergency Stop overrides all movement instantly.
      2. Fallback heuristic predictions are strictly barred from high-speed bins (routed to Bin 4).
      3. Predictions below 0.70 confidence are strictly diverted to Bin 4.
      4. Idempotent command execution via unique event IDs.
      5. Full audit trail persisted in database.
    """
    _emergency_stop_active: bool = False
    _actuators_online: bool = True
    _adapter: BaseSortingAdapter = SimulatedSortingAdapter()

    @classmethod
    def set_emergency_stop(cls, active: bool) -> bool:
        cls._emergency_stop_active = active
        state_str = "ACTIVATED" if active else "CLEARED"
        logger.warning(f"IoT Sorting EMERGENCY STOP {state_str}")
        return cls._emergency_stop_active

    @classmethod
    def is_emergency_stop_active(cls) -> bool:
        return cls._emergency_stop_active

    @classmethod
    def set_actuator_health(cls, online: bool):
        cls._actuators_online = online

    @classmethod
    def is_actuator_online(cls) -> bool:
        return cls._actuators_online

    @classmethod
    def resolve_target_bin(cls, category: str) -> int:
        norm = (category or "").strip().lower()
        if norm in CATEGORY_TO_BIN:
            return CATEGORY_TO_BIN[norm]
        
        # Substring fuzzy match
        for key, bin_idx in CATEGORY_TO_BIN.items():
            if key in norm or norm in key:
                return bin_idx
        return 4 # Unknown -> Bin 4

    @classmethod
    def evaluate_and_dispatch(
        cls,
        db: Session,
        item_label: str,
        detected_category: str,
        confidence: float,
        is_fallback: bool = False,
        prediction_id: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> IoTSortingRecord:
        """
        Validates safety rules, dispatches physical actuator, verifies placement,
        and saves idempotent sorting audit record.
        """
        if not event_id:
            event_id = str(uuid.uuid4())

        # 1. Idempotency Check
        existing = db.query(IoTSortingRecord).filter(IoTSortingRecord.event_id == event_id).first()
        if existing:
            logger.info(f"Returning existing IoT sorting record for event_id={event_id}")
            return existing

        # 2. Safety Rule Evaluation
        # Default safety assumption: route to Bin 4 (Manual Review Chute)
        target_bin_idx = 4
        status = "diverted_to_reject"
        rejection_reason = None

        if cls.is_emergency_stop_active():
            status = "emergency_stopped"
            target_bin_idx = 4
            rejection_reason = "Emergency Stop is active on sorting line; conveyor neutral."
        elif not cls.is_actuator_online():
            status = "blocked_safety"
            target_bin_idx = 4
            rejection_reason = "Physical actuators offline or reported hardware fault."
        elif is_fallback:
            status = "diverted_to_reject"
            target_bin_idx = 4
            rejection_reason = "Fallback heuristic prediction strictly barred from automated diverter actuation (manual review required)."
        elif confidence < CONFIDENCE_SAFETY_THRESHOLD:
            status = "diverted_to_reject"
            target_bin_idx = 4
            rejection_reason = f"Prediction confidence ({confidence:.2f}) is below safety threshold ({CONFIDENCE_SAFETY_THRESHOLD:.2f}); diverted to reject chute."
        else:
            # Safe for automated actuation
            target_bin_idx = cls.resolve_target_bin(detected_category)
            status = "executed"

        target_bin_name = BIN_DEFINITIONS.get(target_bin_idx, {}).get("name", "bin_4_reject_chute")

        # 3. Actuator Dispatch & Feedback Loop
        dispatch_meta = cls._adapter.dispatch(target_bin_idx, event_id)
        verified, verified_dest = cls._adapter.verify_physical_placement(target_bin_idx, event_id)

        # 4. Persistence
        record = IoTSortingRecord(
            event_id=event_id,
            prediction_id=prediction_id,
            item_label=item_label or detected_category,
            detected_category=detected_category,
            confidence=float(confidence),
            is_fallback=is_fallback,
            target_bin=target_bin_name,
            bin_index=target_bin_idx,
            status=status,
            rejection_reason=rejection_reason,
            actuator_id=dispatch_meta.get("actuator_id", "PNEUMATIC_ARM_01"),
            actuator_latency_ms=dispatch_meta.get("latency_ms", 45.0),
            verified_destination=verified_dest if verified else None,
            sensor_verification_status="verified" if verified else "timeout"
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            f"IoT Sorting decision: event={event_id} category='{detected_category}' conf={confidence:.2f} "
            f"fallback={is_fallback} -> bin={target_bin_idx} ({target_bin_name}) status={status}"
        )
        return record

    @classmethod
    def get_system_status(cls, db: Session) -> Dict[str, Any]:
        """Provides real-time actuator health, e-stop flag, and recent execution counts."""
        recent_total = db.query(IoTSortingRecord).count()
        executed_count = db.query(IoTSortingRecord).filter(IoTSortingRecord.status == "executed").count()
        diverted_count = db.query(IoTSortingRecord).filter(IoTSortingRecord.status == "diverted_to_reject").count()
        emergency_count = db.query(IoTSortingRecord).filter(IoTSortingRecord.status == "emergency_stopped").count()

        return {
            "emergency_stop_active": cls.is_emergency_stop_active(),
            "actuators_online": cls.is_actuator_online(),
            "confidence_threshold": CONFIDENCE_SAFETY_THRESHOLD,
            "bins": BIN_DEFINITIONS,
            "statistics": {
                "total_sorting_events": recent_total,
                "executed_to_primary_bins": executed_count,
                "diverted_to_reject_chute": diverted_count,
                "emergency_stopped_events": emergency_count,
                "manual_review_rate_pct": round((diverted_count / recent_total * 100), 2) if recent_total > 0 else 0.0
            }
        }
