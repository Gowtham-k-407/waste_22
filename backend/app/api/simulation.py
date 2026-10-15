from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.services.simulation_engine import SimulationEngine
from app.api import dashboard
from app.core.config import settings

router = APIRouter(prefix="/simulation", tags=["Simulation Mode"])

@router.get("/status")
def get_simulation_status():
    engine = SimulationEngine.get_instance()
    status = engine.get_status()
    # Synchronize dashboard flag
    dashboard.SIMULATION_MODE = status["is_running"]
    return {
        "simulation_mode": status["is_running"],
        "active_label": "SIMULATED DATA / DEMONSTRATION MODE" if status["is_running"] else "HISTORICAL DATA / NEAR REAL-TIME",
        "description": "Simulation engine autonomously generates bounded GPS telemetry, smart bin fill oscillations, overflow alerts, and plant weighbridge tickets.",
        "engine": status
    }

@router.post("/start")
def start_simulation(interval_seconds: float = Query(10.0, ge=2.0, le=300.0, description="Step frequency in seconds")):
    engine = SimulationEngine.get_instance()
    result = engine.start(interval_seconds=interval_seconds)
    dashboard.SIMULATION_MODE = True
    return {
        "success": True,
        "message": f"Simulation started successfully (every {interval_seconds}s).",
        "details": result,
        "badge_label": "SIMULATED DATA",
        "data_source": "simulation"
    }

@router.post("/stop")
def stop_simulation():
    engine = SimulationEngine.get_instance()
    result = engine.stop()
    dashboard.SIMULATION_MODE = False
    return {
        "success": True,
        "message": "Simulation stopped. Systems reverted to historical/recorded operational data.",
        "details": result,
        "badge_label": "HISTORICAL DATA",
        "data_source": "database_operational"
    }

@router.post("/step")
def trigger_simulation_step():
    """Forces an immediate single simulation step without requiring the periodic background worker."""
    engine = SimulationEngine.get_instance()
    result = engine.step_once()
    return {
        "success": True,
        "message": "Executed one discrete simulation cycle.",
        "details": result
    }

@router.post("/toggle")
def toggle_simulation(enabled: Optional[bool] = None):
    engine = SimulationEngine.get_instance()
    if enabled is None:
        target = not engine.is_running
    else:
        target = enabled

    if target:
        result = engine.start()
        dashboard.SIMULATION_MODE = True
    else:
        result = engine.stop()
        dashboard.SIMULATION_MODE = False

    return {
        "success": True,
        "simulation_mode": target,
        "badge_label": "SIMULATED DATA" if target else "HISTORICAL DATA",
        "message": f"Simulation Mode is now {'ENABLED' if target else 'DISABLED'}",
        "details": result
    }
