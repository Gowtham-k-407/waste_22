from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user_from_token
from app.core.database import get_user_db, get_staff_db
from app.models.user import User
from app.models.staff import StaffProfile

# Complete catalog of all 35 Greater Chennai Corporation Municipal Staff Roles
MUNICIPAL_STAFF_ROLES: Dict[str, Dict[str, Any]] = {
    # 1. Executive Leadership
    "municipal_commissioner": {
        "title": "Municipal Commissioner",
        "department": "Executive Leadership",
        "scope": "city_wide",
        "permissions": [
            "dashboard:view_executive", "dashboard:view_operational", "wards:view_all",
            "complaints:view_all", "complaints:escalate", "fleet:view_all",
            "plants:view_all", "reports:view_all", "reports:export", "alerts:view_all"
        ]
    },
    # 2-8. Health & Engineering Supervision
    "municipal_health_officer": {
        "title": "Municipal Health Officer",
        "department": "Public Health & Sanitation",
        "scope": "city_wide",
        "permissions": ["dashboard:view_executive", "wards:view_all", "complaints:view_all", "complaints:manage", "reports:view_all", "alerts:view_all"]
    },
    "environmental_engineer": {
        "title": "Environmental Engineer",
        "department": "Engineering & Environment",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "environmental:view_all", "environmental:manage", "plants:view_all", "reports:export"]
    },
    "assistant_engineer": {
        "title": "Assistant Engineer",
        "department": "Engineering & Maintenance",
        "scope": "zone_level",
        "permissions": ["dashboard:view_operational", "plants:view_all", "plants:maintenance", "fleet:view_all", "alerts:resolve"]
    },
    "sanitary_officer": {
        "title": "Sanitary Officer",
        "department": "Sanitation Operations",
        "scope": "zone_level",
        "permissions": ["dashboard:view_operational", "wards:view_assigned", "complaints:manage", "fleet:view_assigned", "alerts:manage"]
    },
    "sanitary_inspector": {
        "title": "Sanitary Inspector",
        "department": "Sanitation Inspection",
        "scope": "ward_level",
        "permissions": ["dashboard:view_operational", "wards:view_assigned", "complaints:resolve", "complaints:assign", "alerts:view_assigned"]
    },
    "sanitary_supervisor": {
        "title": "Sanitary Supervisor",
        "department": "Sanitation Operations",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "wards:view_assigned", "complaints:resolve", "tasks:manage", "alerts:view_assigned"]
    },
    "ward_sanitation_supervisor": {
        "title": "Ward Sanitation Supervisor",
        "department": "Ward Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "wards:view_assigned", "complaints:resolve", "tasks:assign", "collections:verify"]
    },
    # 9-10. SWM Officers & Coordinators
    "solid_waste_management_officer": {
        "title": "Solid Waste Management Officer",
        "department": "Solid Waste Management",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "wards:view_all", "fleet:manage", "plants:manage", "reports:export"]
    },
    "waste_management_coordinator": {
        "title": "Waste Management Coordinator",
        "department": "Solid Waste Management",
        "scope": "zone_level",
        "permissions": ["dashboard:view_operational", "fleet:dispatch", "plants:view_assigned", "reports:view_all"]
    },
    # 11-16. Field Workers & Drivers
    "garbage_collection_vehicle_driver": {
        "title": "Garbage Collection Vehicle Driver",
        "department": "Logistics & Fleet Operations",
        "scope": "vehicle_level",
        "permissions": ["dashboard:view_field", "vehicle:view_assigned", "vehicle:update_status", "trips:log"]
    },
    "garbage_collection_worker": {
        "title": "Garbage Collection Worker",
        "department": "Field Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "tasks:view_assigned", "tasks:complete", "collections:log"]
    },
    "sanitation_worker": {
        "title": "Sanitation Worker",
        "department": "Field Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "tasks:view_assigned", "tasks:complete"]
    },
    "door_to_door_waste_collection_worker": {
        "title": "Door-to-Door Waste Collection Worker",
        "department": "Field Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "tasks:view_assigned", "collections:record_segregation"]
    },
    "street_sweeper": {
        "title": "Street Sweeper",
        "department": "Field Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "tasks:view_assigned", "tasks:complete"]
    },
    "public_waste_bin_cleaning_worker": {
        "title": "Public Waste Bin Cleaning Worker",
        "department": "Field Sanitation",
        "scope": "ward_level",
        "permissions": ["dashboard:view_field", "bins:view_assigned", "bins:clear_overflow"]
    },
    # 17-21. Facility & Processing Workers
    "waste_segregation_worker": {
        "title": "Waste Segregation Worker",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "facility:view_assigned", "segregation:record"]
    },
    "material_recovery_facility_worker": {
        "title": "Material Recovery Facility Worker",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "facility:view_assigned", "recyclables:log"]
    },
    "recycling_facility_worker": {
        "title": "Recycling Facility Worker",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "facility:view_assigned", "recyclables:log"]
    },
    "composting_facility_worker": {
        "title": "Composting Facility Worker",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "facility:view_assigned", "compost:log"]
    },
    "waste_processing_plant_operator": {
        "title": "Waste Processing Plant Operator",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_operational", "facility:view_assigned", "facility:operate", "intake:record"]
    },
    # 22-25. Logistics & Data Entry
    "waste_transportation_worker": {
        "title": "Waste Transportation Worker",
        "department": "Logistics & Fleet Operations",
        "scope": "vehicle_level",
        "permissions": ["dashboard:view_field", "vehicle:view_assigned", "trips:log"]
    },
    "waste_collection_vehicle_operator": {
        "title": "Waste Collection Vehicle Operator",
        "department": "Logistics & Fleet Operations",
        "scope": "vehicle_level",
        "permissions": ["dashboard:view_field", "vehicle:operate", "trips:log"]
    },
    "waste_weighbridge_operator": {
        "title": "Waste Weighbridge Operator",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "facility:view_assigned", "weighbridge:record"]
    },
    "waste_management_data_entry_operator": {
        "title": "Waste Management Data Entry Operator",
        "department": "Data & Administration",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "records:entry", "reports:view_all"]
    },
    # 26-30. Control Room & Quality Officers
    "municipal_control_room_operator": {
        "title": "Municipal Control Room Operator",
        "department": "Control & Command",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "fleet:view_all", "alerts:manage", "complaints:view_all", "iot:view_all"]
    },
    "waste_management_data_analyst": {
        "title": "Waste Management Data Analyst",
        "department": "Data & Analytics",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "reports:view_all", "reports:export", "analytics:view_all"]
    },
    "environmental_monitoring_officer": {
        "title": "Environmental Monitoring Officer",
        "department": "Environmental Compliance",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "environmental:view_all", "compliance:inspect", "reports:view_all"]
    },
    "public_sanitation_complaint_officer": {
        "title": "Public Sanitation Complaint Officer",
        "department": "Public Grievance",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "complaints:view_all", "complaints:manage", "complaints:assign", "complaints:resolve"]
    },
    "waste_management_inspection_officer": {
        "title": "Waste Management Inspection Officer",
        "department": "Quality & Inspection",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "inspections:conduct", "ai:review_contributions", "alerts:manage"]
    },
    # 31-35. Specialized Roles
    "waste_disposal_facility_supervisor": {
        "title": "Waste Disposal Facility Supervisor",
        "department": "Processing Facilities",
        "scope": "facility_level",
        "permissions": ["dashboard:view_operational", "facility:view_assigned", "facility:manage", "safety:inspect"]
    },
    "hazardous_household_waste_handling_worker": {
        "title": "Hazardous Household Waste Handling Worker",
        "department": "Specialized Waste",
        "scope": "facility_level",
        "permissions": ["dashboard:view_field", "hazardous:handle", "tasks:view_assigned"]
    },
    "e_waste_collection_worker": {
        "title": "E-Waste Collection Worker",
        "department": "Specialized Waste",
        "scope": "zone_level",
        "permissions": ["dashboard:view_field", "ewaste:collect", "tasks:view_assigned"]
    },
    "waste_management_project_manager": {
        "title": "Waste Management Project Manager",
        "department": "Projects & Modernization",
        "scope": "city_wide",
        "permissions": ["dashboard:view_executive", "reports:view_all", "ai:view_all", "fleet:view_all", "plants:view_all"]
    },
    "public_awareness_community_outreach_officer": {
        "title": "Public Awareness and Community Outreach Officer",
        "department": "Public Relations & Education",
        "scope": "city_wide",
        "permissions": ["dashboard:view_operational", "education:manage", "campaigns:manage", "contributions:view"]
    }
}

# Legacy role mappings for backward compatibility
LEGACY_ROLE_MAP = {
    "system_admin": ["*"],
    "ai_admin": ["ai:view_all", "ai:manage", "ai:review_contributions", "dashboard:view_operational"],
    "municipal_officer": ["dashboard:view_operational", "wards:view_all", "complaints:manage", "fleet:view_all", "reports:view_all"],
    "plant_operator": ["dashboard:view_operational", "facility:view_assigned", "facility:operate", "intake:record", "weighbridge:record"],
    "contributor": ["public:contribute", "public:view"],
    "public": ["public:view"]
}

ADMIN_ROLES = {"ai_admin", "system_admin", "municipal_officer", "municipal_commissioner", "solid_waste_management_officer"}

def get_role_permissions(role: str) -> List[str]:
    if role == "system_admin":
        return ["*"]
    if role in MUNICIPAL_STAFF_ROLES:
        return MUNICIPAL_STAFF_ROLES[role]["permissions"]
    return LEGACY_ROLE_MAP.get(role, ["public:view"])

def require_roles(allowed_roles: List[str]):
    """FastAPI Dependency enforcing role authorization."""
    def role_checker(current_user: User = Depends(get_current_user_from_token)):
        # System Admin always passes role checks
        if current_user.role == "system_admin":
            return current_user
        if current_user.role in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {', '.join(allowed_roles)}. Your role: '{current_user.role}'."
        )
    return role_checker

def require_permission(permission: str):
    """FastAPI Dependency enforcing specific granular permission."""
    def permission_checker(current_user: User = Depends(get_current_user_from_token)):
        if current_user.role == "system_admin":
            return current_user
        perms = get_role_permissions(current_user.role)
        if "*" in perms or permission in perms:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required capability: '{permission}'."
        )
    return permission_checker

def verify_ward_scope(current_user: User, ward_number: int, staff_db: Session) -> bool:
    """
    Enforces geographic scope: Checks if staff user is authorized to view or mutate records for a ward.
    System admin, executive roles, and city-wide officers have global access.
    Ward-level supervisors are strictly constrained to their assigned ward.
    """
    if current_user.role == "system_admin":
        return True
    
    # Check if role has city_wide scope
    role_meta = MUNICIPAL_STAFF_ROLES.get(current_user.role)
    if role_meta and role_meta.get("scope") == "city_wide":
        return True

    # Check staff profile in Database B
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not staff_profile:
        # Public or unassigned user has read-only public access
        return True

    if staff_profile.assigned_ward_number is not None:
        if staff_profile.assigned_ward_number == ward_number:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access restricted: Your staff assignment is for Ward {staff_profile.assigned_ward_number}, but this action is for Ward {ward_number}."
        )

    return True

def verify_facility_scope(current_user: User, facility_id: int, staff_db: Session) -> bool:
    """Enforces facility scope for plant and weighbridge operators."""
    if current_user.role == "system_admin":
        return True
    
    role_meta = MUNICIPAL_STAFF_ROLES.get(current_user.role)
    if role_meta and role_meta.get("scope") == "city_wide":
        return True

    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if staff_profile and staff_profile.assigned_facility_id is not None:
        if staff_profile.assigned_facility_id == facility_id:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access restricted: Your assignment is for Facility #{staff_profile.assigned_facility_id}, not Facility #{facility_id}."
        )

    return True

# Comprehensive catalog list for staff portal
GCC_STAFF_ROLES = [
    {
        "role_id": k,
        "title": v["title"],
        "department": v["department"],
        "scope_level": v["scope"],
        "description": f"GCC {v['title']} responsible for {v['department']}.",
        "permissions": v["permissions"]
    }
    for k, v in MUNICIPAL_STAFF_ROLES.items()
]

def get_role_info(role_name_or_id: str) -> Optional[Dict[str, Any]]:
    for k, v in MUNICIPAL_STAFF_ROLES.items():
        if k == role_name_or_id or v["title"].lower() == role_name_or_id.lower():
            return {
                "role_id": k,
                "title": v["title"],
                "department": v["department"],
                "scope_level": v["scope"],
                "description": f"GCC {v['title']} responsible for {v['department']}.",
                "permissions": v["permissions"]
            }
    return None

