from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.core.database import get_user_db, get_staff_db, get_waste_db
from app.models.user import User
from app.models.staff import StaffProfile, StaffDutyAssignment
from app.models.ward import Ward
from app.models.vehicle import CollectionVehicle
from app.models.plant import SegregationPlant
from app.models.alert import Alert
from app.models.complaint import PublicComplaint, Notification, WeighbridgeRecord
from app.models.iot import IoTDevice, DeviceTelemetry
from app.core.security import get_current_user_optional, get_current_user, get_current_user_from_token
from app.core.rbac import GCC_STAFF_ROLES, get_role_info

router = APIRouter(prefix="/staff", tags=["Municipal Staff Portal & Role-Specific Dashboards"])

@router.get("/roles")
def get_all_roles():
    """Returns the comprehensive GCC catalog of all 35 municipal staff roles with descriptions and departments."""
    return {
        "total_roles": len(GCC_STAFF_ROLES),
        "roles": [
            {
                "role_id": r["role_id"],
                "role_name": r["title"],
                "department": r["department"],
                "scope_level": r["scope_level"],
                "description": r["description"],
                "default_permissions": r["permissions"]
            }
            for r in GCC_STAFF_ROLES
        ]
    }

@router.get("/profiles")
def list_staff_profiles(
    department: Optional[str] = Query(None),
    ward_id: Optional[int] = Query(None),
    role_name: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    user_db: Session = Depends(get_user_db)
):
    """
    Returns municipal staff profiles from Database B (Staff DB) joined with User account metadata from Database A.
    Restricted to GCC municipal personnel and administrators.
    """
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Staff directory is restricted to GCC municipal staff and administrators."
        )

    query = staff_db.query(StaffProfile)
    if department:
        query = query.filter(StaffProfile.department == department)
    if ward_id:
        query = query.filter(StaffProfile.assigned_ward_id == ward_id)
    if role_name:
        query = query.filter((StaffProfile.job_title == role_name) | (StaffProfile.role_code == role_name))

    profiles = query.order_by(StaffProfile.id.asc()).all()
    results = []
    for p in profiles:
        # Cross-database lookup in User DB
        user = user_db.query(User).filter(User.id == p.user_id).first()
        results.append({
            "id": p.id,
            "employee_id": p.employee_id,
            "full_name": user.full_name if user else f"Officer {p.employee_id}",
            "email": user.email if user else None,
            "role_title": p.job_title,
            "role_code": p.role_code,
            "department": p.department,
            "assigned_ward_id": p.assigned_ward_id,
            "assigned_zone_number": p.assigned_zone_number,
            "assigned_facility_id": p.assigned_facility_id,
            "employment_status": p.employment_status,
            "shift": p.shift,
            "phone_number": p.phone_number
        })

    return {"count": len(results), "profiles": results}

@router.get("/dashboard")
def get_staff_role_dashboard(
    role_override: Optional[str] = Query(None, description="Preview dashboard for any of the 35 GCC roles (Admin only)"),
    current_user: User = Depends(get_current_user_from_token),
    waste_db: Session = Depends(get_waste_db),
    staff_db: Session = Depends(get_staff_db)
):
    """
    Delivers a dedicated, tailored operational dashboard for each of the 35 GCC Municipal Staff roles.
    Includes role-specific KPIs, tasks, alerts, operational routes, and controls.
    Non-admins are strictly restricted to their assigned server-side role.
    """
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Municipal staff credentials required to access the Staff Dashboard."
        )

    # Only System Administrator may preview other roles
    if current_user.role == "system_admin":
        target_role = role_override or "Municipal Commissioner"
    else:
        if role_override and role_override != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You cannot view dashboards for other municipal roles ({role_override}). You are assigned as '{current_user.role}'."
            )
        target_role = current_user.role

    role_info = get_role_info(target_role)
    if not role_info:
        target_role = current_user.role
        role_info = get_role_info(target_role) or {
            "department": "Municipal Operations",
            "scope_level": "city_wide",
            "description": f"GCC {target_role}",
            "permissions": ["dashboard:view_operational"]
        }

    # Fetch staff profile from Database B
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()

    assigned_ward = staff_profile.assigned_ward_id if staff_profile and staff_profile.assigned_ward_id else 102
    assigned_facility = staff_profile.assigned_facility_id if staff_profile and staff_profile.assigned_facility_id else 1

    # Base common aggregates
    total_complaints = waste_db.query(PublicComplaint).count()
    active_complaints = waste_db.query(PublicComplaint).filter(PublicComplaint.status.in_(["submitted", "assigned", "in_progress"])).count()
    active_alerts = waste_db.query(Alert).filter(Alert.status == "active").count()

    response: Dict[str, Any] = {
        "role_name": target_role,
        "department": role_info["department"],
        "scope_level": role_info["scope_level"],
        "description": role_info["description"],
        "permissions": role_info["permissions"],
        "assigned_ward_id": assigned_ward,
        "assigned_facility_id": assigned_facility,
        "data_provenance": "SIMULATED DATA (Real-Time Engine)" if active_alerts > 0 else "HISTORICAL DATA"
    }

    # 1. Executive Roles (Commissioner, Health Officer, Environmental Engineer, Project Manager)
    if target_role in ("Municipal Commissioner", "Municipal Health Officer", "Environmental Engineer", "Waste Management Project Manager"):
        wards = waste_db.query(Ward).all()
        total_tonnage = round(sum(w.daily_waste_tons for w in wards), 1) if wards else 5420.0
        avg_seg = round(sum(w.segregation_efficiency for w in wards) / len(wards), 1) if wards else 61.4
        
        response["kpis"] = [
            {"label": "City Waste Generation", "value": f"{total_tonnage:,.1f} TPD", "trend": "+1.8%", "status": "normal"},
            {"label": "Segregation Efficiency", "value": f"{avg_seg}%", "trend": "+3.1%", "status": "good"},
            {"label": "Active City Complaints", "value": str(active_complaints), "trend": "-5.4%", "status": "warning" if active_complaints > 10 else "normal"},
            {"label": "Active Fleet Operations", "value": "24 Vehicles", "trend": "100% active", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {"id": "TSK-01", "task": "Review Q3 Municipal Landfill Diversion Target (75% Goal)", "priority": "high", "due": "Today 18:00"},
            {"id": "TSK-02", "task": "Approve Resource Re-allocation for Zone 8 Compactor Fleet", "priority": "medium", "due": "Tomorrow 11:00"}
        ]
        response["quick_actions"] = ["Export City Waste Audit", "Broadcast Zone Advisory", "Review Escalated Grievances"]

    # 2. Ward Sanitation Supervisors & Inspectors
    elif target_role in ("Sanitary Officer", "Sanitary Inspector", "Sanitary Supervisor", "Ward Sanitation Supervisor", "Assistant Engineer", "Solid Waste Management Officer", "Waste Management Coordinator"):
        ward = waste_db.query(Ward).filter(Ward.ward_number == assigned_ward).first()
        ward_complaints = waste_db.query(PublicComplaint).filter(PublicComplaint.ward_id == assigned_ward).all()
        ward_bins = waste_db.query(IoTDevice).filter(IoTDevice.ward_id == assigned_ward).all()

        response["kpis"] = [
            {"label": f"Ward {assigned_ward} Daily Collection", "value": f"{ward.daily_waste_tons if ward else 28.5} TPD", "trend": "+0.5%", "status": "normal"},
            {"label": "Ward Segregation Rate", "value": f"{ward.segregation_efficiency if ward else 68.0}%", "trend": "+2.0%", "status": "good"},
            {"label": "Pending Ward Grievances", "value": str(len([c for c in ward_complaints if c.status != 'resolved'])), "trend": "Active SLA", "status": "warning"},
            {"label": "Monitored Smart Bins", "value": f"{len(ward_bins)} Online", "trend": "100%", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {"id": f"WRD-TSK-{c.id}", "task": f"Inspect Grievance #{c.tracking_number}: {c.category.replace('_', ' ').title()} at {c.location_address}", "priority": c.priority, "due": "Within 24h"}
            for c in ward_complaints[:4]
        ] or [{"id": "WRD-TSK-01", "task": f"Conduct door-to-door source segregation spot-check in Ward {assigned_ward}", "priority": "medium", "due": "Today"}]
        response["quick_actions"] = ["Dispatch Mobile Sweeper", "Acknowledge Grievance", "Inspect Commercial Street Bins"]

    # 3. Vehicle Drivers & Operators
    elif target_role in ("Garbage Collection Vehicle Driver", "Waste Collection Vehicle Operator", "Waste Transportation Worker"):
        truck = waste_db.query(CollectionVehicle).first()
        response["kpis"] = [
            {"label": "Assigned Vehicle", "value": truck.vehicle_number if truck else "TN-01-GCC-2001", "status": "good"},
            {"label": "Current Load", "value": f"{truck.current_load_tons if truck else 3.8} / {truck.capacity_tons if truck else 6.0} Tons", "status": "normal"},
            {"label": "Route Status", "value": "Ward 105 Secondary Circuit", "status": "active"},
            {"label": "Completed Pickups", "value": "18 / 24 Checkpoints", "trend": "75%", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {"id": "RTE-CP-19", "task": "Commercial Bin Point #19: Anna Nagar Roundtana (Near Metro)", "priority": "high", "due": "ETA 15 mins"},
            {"id": "RTE-CP-20", "task": "Apartment Bulk Waste: Shanti Colony Block C", "priority": "medium", "due": "ETA 35 mins"},
            {"id": "RTE-CP-21", "task": "Transit to Koyambedu Transfer Station for Unloading", "priority": "normal", "due": "ETA 60 mins"}
        ]
        response["quick_actions"] = ["Mark Checkpoint Completed", "Report Traffic Obstruction", "Log Breakdown SOS"]

    # 4. Weighbridge Operators
    elif target_role == "Waste Weighbridge Operator":
        recent_tickets = waste_db.query(WeighbridgeRecord).order_by(WeighbridgeRecord.gross_time.desc()).limit(5).all()
        response["kpis"] = [
            {"label": "Tickets Logged Today", "value": f"{len(recent_tickets) + 18}", "trend": "+12 vs yesterday", "status": "normal"},
            {"label": "Net Tonnage Weighed", "value": "142.8 Tons", "trend": "+4.2%", "status": "good"},
            {"label": "Weighbridge Scale Status", "value": "Calibrated (Zero: 0.0 kg)", "status": "good"},
            {"label": "Average Turnaround Time", "value": "3.5 Mins", "trend": "Fast", "status": "good"}
        ]
        response["recent_tickets"] = [
            {
                "ticket_number": t.ticket_number,
                "vehicle_number": t.vehicle_number,
                "plant_name": t.plant_name,
                "net_weight_kg": t.net_weight_kg,
                "gross_time": t.gross_time.strftime("%H:%M:%S") if t.gross_time else None
            }
            for t in recent_tickets
        ]
        response["quick_actions"] = ["Capture Gross Weight", "Capture Tare Weight", "Print Municipal Weighment Slip"]

    # 5. Facility Operators (MRF, Composting, Recycling, Processing)
    elif target_role in ("Material Recovery Facility Worker", "Recycling Facility Worker", "Composting Facility Worker", "Waste Processing Plant Operator", "Waste Disposal Facility Supervisor"):
        plant = waste_db.query(SegregationPlant).first()
        response["kpis"] = [
            {"label": "Facility Intake Today", "value": f"{plant.current_input_tpd if plant else 340.0} TPD", "trend": "Active Line", "status": "normal"},
            {"label": "Design Capacity", "value": f"{plant.capacity_tpd if plant else 500.0} TPD", "status": "normal"},
            {"label": "Sorting Line Efficiency", "value": f"{plant.efficiency_pct if plant else 88.5}%", "trend": "+1.2%", "status": "good"},
            {"label": "Baled Recyclables Stock", "value": "42.5 Tons", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {"id": "FAC-01", "task": "Optical Sorter Calibration on Line 2 (PET vs HDPE)", "priority": "high", "due": "Today 16:00"},
            {"id": "FAC-02", "task": "Inspect Composting Windrow #4 Temperature (Target: 55-65°C)", "priority": "medium", "due": "Today 17:30"}
        ]
        response["quick_actions"] = ["Log Baling Batch", "Report Conveyor Jam", "Update Shift Handover"]

    # 6. Grievance & Inspection Officers
    elif target_role in ("Public Sanitation Complaint Officer", "Waste Management Inspection Officer"):
        complaints = waste_db.query(PublicComplaint).order_by(PublicComplaint.created_at.desc()).limit(6).all()
        response["kpis"] = [
            {"label": "Assigned Grievances", "value": f"{len(complaints)}", "status": "normal"},
            {"label": "Resolved Within SLA", "value": "91.2%", "trend": "+3.0%", "status": "good"},
            {"label": "Escalated Grievances", "value": "2 Cases", "status": "warning"},
            {"label": "Average Resolution Time", "value": "18.4 Hours", "trend": "Under 24h SLA", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {
                "id": f"GRV-{c.id}",
                "task": f"Verify Resolution for #{c.tracking_number}: {c.category.replace('_', ' ').title()}",
                "location": c.location_address,
                "priority": c.priority
            }
            for c in complaints
        ]
        response["quick_actions"] = ["Verify Photo Proof", "Reassign to Sanitary Inspector", "Close Complaint"]

    # 7. Control Room & Data Analysts (Default for remaining roles)
    else:
        response["kpis"] = [
            {"label": "Active GPS Monitored Units", "value": "24 / 24 Online", "status": "good"},
            {"label": "Smart Bins Telemetry Stream", "value": "Normal (15s interval)", "status": "good"},
            {"label": "City-wide Overflow Risk", "value": f"{active_alerts} Alerts", "status": "warning" if active_alerts > 0 else "good"},
            {"label": "Municipal AI Vision Ingestion", "value": "Active", "status": "good"}
        ]
        response["actionable_tasks"] = [
            {"id": "CR-01", "task": "Monitor Smart Compactor Bin BIN-ZN08-W102 high-fill telemetry", "priority": "high", "due": "Immediate"},
            {"id": "CR-02", "task": "Generate Weekly Zonal Waste Diversion Performance Report", "priority": "medium", "due": "Today 17:00"}
        ]
        response["quick_actions"] = ["Broadcast Fleet Alert", "Trigger Dynamic Reroute", "Export Analytical Manifest"]

    return response
