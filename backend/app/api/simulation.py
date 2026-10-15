from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.services.simulation_engine import SimulationEngine
from app.api import dashboard
from app.core.config import settings
from app.core.database import get_user_db
from app.core.rbac import require_roles
from app.models.user import User, AuthAuditLog

router = APIRouter(prefix="/simulation", tags=["Simulation Mode"])

ADMIN_SIMULATION_ROLES = ["system_admin", "municipal_officer", "ai_admin"]

@router.get("/status")
def get_simulation_status():
    engine = SimulationEngine.get_instance()
    status_info = engine.get_status()
    # Synchronize dashboard flag
    dashboard.SIMULATION_MODE = status_info["is_running"]
    return {
        "simulation_mode": status_info["is_running"],
        "active_label": "SIMULATED DATA / DEMONSTRATION MODE" if status_info["is_running"] else "HISTORICAL DATA / NEAR REAL-TIME",
        "description": "Simulation engine autonomously generates bounded GPS telemetry, smart bin fill oscillations, overflow alerts, and plant weighbridge tickets.",
        "engine": status_info
    }

@router.post("/start")
def start_simulation(
    interval_seconds: float = Query(10.0, ge=2.0, le=300.0, description="Step frequency in seconds"),
    current_user: User = Depends(require_roles(ADMIN_SIMULATION_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    engine = SimulationEngine.get_instance()
    result = engine.start(interval_seconds=interval_seconds)
    dashboard.SIMULATION_MODE = True

    audit = AuthAuditLog(user_id=current_user.id, action="simulation_started")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "message": f"Simulation started successfully (every {interval_seconds}s).",
        "details": result,
        "badge_label": "SIMULATED DATA",
        "data_source": "simulation"
    }

@router.post("/stop")
def stop_simulation(
    current_user: User = Depends(require_roles(ADMIN_SIMULATION_ROLES)),
    user_db: Session = Depends(get_user_db)
):
    engine = SimulationEngine.get_instance()
    result = engine.stop()
    dashboard.SIMULATION_MODE = False

    audit = AuthAuditLog(user_id=current_user.id, action="simulation_stopped")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "message": "Simulation stopped. Systems reverted to historical/recorded operational data.",
        "details": result,
        "badge_label": "HISTORICAL DATA",
        "data_source": "database_operational"
    }

@router.post("/step")
def trigger_simulation_step(
    current_user: User = Depends(require_roles(ADMIN_SIMULATION_ROLES))
):
    """Forces an immediate single simulation step without requiring the periodic background worker."""
    engine = SimulationEngine.get_instance()
    result = engine.step_once()
    return {
        "success": True,
        "message": "Executed one discrete simulation cycle.",
        "details": result
    }

@router.post("/toggle")
def toggle_simulation(
    enabled: Optional[bool] = None,
    current_user: User = Depends(require_roles(ADMIN_SIMULATION_ROLES)),
    user_db: Session = Depends(get_user_db)
):
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

    audit = AuthAuditLog(user_id=current_user.id, action=f"simulation_toggled_{'on' if target else 'off'}")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "simulation_mode": target,
        "badge_label": "SIMULATED DATA" if target else "HISTORICAL DATA",
        "message": f"Simulation Mode is now {'ENABLED' if target else 'DISABLED'}",
        "details": result
    }
