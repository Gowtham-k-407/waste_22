import time
import math
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.database import WasteSessionLocal
from app.models.vehicle import CollectionVehicle
from app.models.ward import Ward
from app.models.plant import SegregationPlant
from app.models.alert import Alert
from app.models.iot import IoTDevice, DeviceTelemetry
from app.models.complaint import SimulationRun, WeighbridgeRecord

logger = logging.getLogger("wastedash.simulation_engine")

class SimulationEngine:
    _instance: Optional["SimulationEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._interval_seconds = 10.0
        self._step_counter = 0
        self._current_run_id: Optional[str] = None
        self._last_step_time: Optional[datetime] = None
        self._last_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "SimulationEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = SimulationEngine()
            return cls._instance

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self._running,
            "simulation_run_id": self._current_run_id,
            "step_count": self._step_counter,
            "interval_seconds": self._interval_seconds,
            "last_step_time": self._last_step_time.isoformat() if self._last_step_time else None,
            "data_source": "simulation",
            "is_simulated": True,
            "active_badge": "SIMULATED DATA / DEMONSTRATION MODE" if self._running else "REAL / HISTORICAL DATA",
            "last_error": self._last_error
        }

    def start(self, interval_seconds: float = 10.0) -> Dict[str, Any]:
        with self._lock:
            if self._running:
                return {"status": "already_running", "run_id": self._current_run_id}

            self._interval_seconds = max(2.0, min(300.0, float(interval_seconds)))
            self._stop_event.clear()
            self._step_counter = 0
            self._current_run_id = f"SIM-RUN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            self._running = True

            # Register run in database
            db = WasteSessionLocal()
            try:
                run_record = SimulationRun(
                    simulation_run_id=self._current_run_id,
                    status="running",
                    tick_interval_seconds=int(self._interval_seconds),
                    events_generated=0,
                    last_tick_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                db.add(run_record)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not record SimulationRun in DB: {e}")
            finally:
                db.close()

            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="WasteDashSimulationWorker")
            self._thread.start()
            logger.info(f"Simulation engine started with run_id={self._current_run_id}, interval={self._interval_seconds}s")
            return {"status": "started", "run_id": self._current_run_id, "interval_seconds": self._interval_seconds}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if not self._running:
                return {"status": "not_running"}

            self._running = False
            self._stop_event.set()

            # Finalize run in database
            db = WasteSessionLocal()
            try:
                run_record = db.query(SimulationRun).filter(SimulationRun.simulation_run_id == self._current_run_id).first()
                if run_record:
                    run_record.status = "stopped"
                    run_record.last_tick_at = datetime.utcnow()
                    run_record.events_generated = self._step_counter
                    db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not update SimulationRun in DB: {e}")
            finally:
                db.close()

            logger.info(f"Simulation engine stopped. Total steps executed: {self._step_counter}")
            return {"status": "stopped", "run_id": self._current_run_id, "total_steps": self._step_counter}

    def step_once(self) -> Dict[str, Any]:
        """Executes a single discrete simulation iteration."""
        if not self._current_run_id:
            self._current_run_id = f"SIM-STEP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        return self._execute_simulation_step()

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                self._execute_simulation_step()
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"Error in simulation loop: {e}", exc_info=True)

            self._stop_event.wait(timeout=self._interval_seconds)

    def _execute_simulation_step(self) -> Dict[str, Any]:
        self._step_counter += 1
        now = datetime.utcnow()
        self._last_step_time = now
        step_events = 0

        db = WasteSessionLocal()
        try:
            # 1. Simulate Vehicle GPS & Progress along Chennai Routes
            vehicles = db.query(CollectionVehicle).limit(24).all()
            for v in vehicles:
                angle = (self._step_counter * 0.15) + (v.id * 0.4)
                lat_offset = 0.0025 * math.sin(angle)
                lng_offset = 0.0025 * math.cos(angle)

                base_lat = v.latitude or (13.0827 + (v.id % 15) * 0.01)
                base_lng = v.longitude or (80.2707 - (v.id % 10) * 0.008)

                v.latitude = round(base_lat + lat_offset, 6)
                v.longitude = round(base_lng + lng_offset, 6)
                
                v.current_fill_pct = round(min(100.0, max(10.0, (v.current_fill_pct or 40.0) + 2.5)), 1)
                if v.current_fill_pct >= 95.0:
                    v.status = "in_transit"
                else:
                    v.status = "collecting"

                step_events += 1

            # 2. Simulate Smart Bins & Telemetry
            devices = db.query(IoTDevice).filter(IoTDevice.device_type == "smart_bin").limit(10).all()
            for dev in devices:
                fill = round(min(98.0, max(15.0, 50.0 + 35.0 * math.sin(self._step_counter * 0.2 + dev.id))), 1)
                distance_cm = round(max(5.0, 100.0 - fill), 1)
                weight_kg = round(fill * 0.42, 1)

                dev.last_fill_percentage = fill
                dev.last_ping = now
                dev.status = "online"

                telemetry = DeviceTelemetry(
                    device_id=dev.device_id,
                    bin_fill_pct=fill,
                    distance_cm=distance_cm,
                    weight_kg=weight_kg,
                    battery_pct=round(max(40.0, 95.0 - (self._step_counter * 0.01)), 1),
                    temperature_c=round(30.0 + 2.0 * math.sin(self._step_counter * 0.1), 1),
                    humidity_pct=round(65.0 + 4.0 * math.cos(self._step_counter * 0.1), 1),
                    timestamp=now,
                    is_simulated=True,
                    data_source="simulation"
                )
                db.add(telemetry)
                step_events += 1

                # 3. Create Operational Alert if Bin is Overflowing
                if fill >= 88.0:
                    existing_recent_alert = db.query(Alert).filter(
                        Alert.ward_number == dev.ward_number,
                        Alert.category == "Accumulation",
                        Alert.status == "Active"
                    ).first()

                    if not existing_recent_alert:
                        new_alert = Alert(
                            alert_code=f"ALT-SIM-{now.strftime('%Y%m%d%H%M%S')}-{dev.id}",
                            priority="High" if fill >= 92.0 else "Medium",
                            category="Accumulation",
                            location_name=f"Smart Bin Ward {dev.ward_number}",
                            ward_number=dev.ward_number,
                            issue=f"Smart Bin {dev.device_id} reached {fill}% fill level.",
                            recommended_action="Dispatch compactor truck to clear smart bin before overflow occurs.",
                            status="Active",
                            timestamp=now
                        )
                        db.add(new_alert)
                        step_events += 1

            # 4. Periodically generate a simulated Weighbridge Record
            if self._step_counter % 4 == 0:
                plant = db.query(SegregationPlant).first()
                if plant and vehicles:
                    truck = vehicles[self._step_counter % len(vehicles)]
                    gross_tons = round(12.0 + (truck.current_fill_pct / 100.0) * 5.0, 2)
                    tare_tons = 7.5
                    net_tons = round(gross_tons - tare_tons, 2)

                    ticket_no = f"WB-SIM-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
                    ticket = WeighbridgeRecord(
                        ticket_number=ticket_no,
                        facility_id=plant.id,
                        facility_name=plant.name,
                        vehicle_code=truck.vehicle_code,
                        gross_weight_tons=gross_tons,
                        tare_weight_tons=tare_tons,
                        net_weight_tons=net_tons,
                        primary_waste_category="Mixed Waste",
                        source_ward_number=truck.assigned_ward_id or 102,
                        operator_name="Synthetic Scale Terminal",
                        is_simulated=True,
                        data_source="simulation",
                        timestamp=now
                    )
                    db.add(ticket)
                    step_events += 1

            # 5. Clean up old simulated telemetry
            total_telemetry = db.query(DeviceTelemetry).filter(DeviceTelemetry.is_simulated == True).count()
            if total_telemetry > 500:
                oldest_ids = db.query(DeviceTelemetry.id).filter(
                    DeviceTelemetry.is_simulated == True
                ).order_by(DeviceTelemetry.id.asc()).limit(100).all()
                if oldest_ids:
                    id_list = [i[0] for i in oldest_ids]
                    db.query(DeviceTelemetry).filter(DeviceTelemetry.id.in_(id_list)).delete(synchronize_session=False)

            # Update simulation run stats
            if self._current_run_id:
                run_record = db.query(SimulationRun).filter(SimulationRun.simulation_run_id == self._current_run_id).first()
                if run_record:
                    run_record.events_generated = self._step_counter
                    run_record.last_tick_at = now

            db.commit()
            return {
                "success": True,
                "step": self._step_counter,
                "run_id": self._current_run_id,
                "events_generated": step_events,
                "timestamp": now.isoformat()
            }
        except Exception as e:
            db.rollback()
            self._last_error = str(e)
            logger.error(f"Simulation step failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()
