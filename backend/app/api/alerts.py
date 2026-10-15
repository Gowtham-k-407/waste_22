from fastapi import APIRouter, Depends, HTTPException, status as http_status, Security
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db, get_user_db, get_staff_db
from app.core.security import get_current_user_from_token
from app.core.rbac import get_role_permissions, verify_ward_scope, MUNICIPAL_STAFF_ROLES
from app.models.user import User, AuthAuditLog
from app.models.staff import StaffProfile, StaffAuditLog
from app.models.optimization import OperationalAlert
from app.schemas.common_schemas import AlertSchema

router = APIRouter(prefix="/alerts", tags=["Alert System"])

ALERT_RESOLVE_PERMISSIONS = {"alerts:resolve", "alerts:manage", "*"}
ALERT_RESOLVE_ROLES = {
    "system_admin", "assistant_engineer", "sanitary_officer",
    "municipal_control_room_operator", "waste_management_inspection_officer",
    "solid_waste_management_officer", "municipal_commissioner", "municipal_officer"
}

@router.get("/", response_model=List[AlertSchema])
def get_alerts(
    priority: Optional[str] = None,
    status: Optional[str] = "Active",
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    db: Session = Depends(get_db)
):
    """
    Retrieve operational alerts. Strictly restricted to GCC municipal staff and administrators.
    Ordinary public/contributor users are denied access.
    Ward-level staff only see alerts relevant to their assigned scope.
    """
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied: Operational municipal alerts are restricted to GCC municipal personnel and administrators."
        )

    query = db.query(OperationalAlert)

    # Ward-level filtering for assigned field officers
    perms = get_role_permissions(current_user.role)
    if "alerts:view_all" not in perms and "*" not in perms and current_user.role != "system_admin":
        staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if staff_profile and staff_profile.assigned_ward_number is not None:
            query = query.filter(OperationalAlert.ward_number == staff_profile.assigned_ward_number)

    if priority:
        query = query.filter(OperationalAlert.priority == priority)
    if status:
        query = query.filter(OperationalAlert.status == status)

    return query.order_by(OperationalAlert.timestamp.desc()).all()


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    user_db: Session = Depends(get_user_db),
    db: Session = Depends(get_db)
):
    """
    Resolve an operational alert.
    Requires authenticated GCC staff credentials with alert resolution authority.
    Enforces organizational and geographic ward scope checks.
    Records structured audit log events on resolution.
    """
    # 1. Authentication is enforced by Depends(get_current_user_from_token)
    # 2. Authorization check: Role must have resolve/manage permission
    user_perms = get_role_permissions(current_user.role)
    has_resolve_perm = bool(set(user_perms).intersection(ALERT_RESOLVE_PERMISSIONS))
    is_authorized_role = current_user.role in ALERT_RESOLVE_ROLES or current_user.role == "system_admin"

    if not (has_resolve_perm or is_authorized_role):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: User role '{current_user.role}' lacks authority to resolve operational alerts."
        )

    # 3. Locate alert in Database C
    alert = db.query(OperationalAlert).filter(OperationalAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found."
        )

    # 4. Scope verification: Ward-scoped personnel cannot resolve alerts outside their assigned ward
    if alert.ward_number is not None and current_user.role != "system_admin":
        verify_ward_scope(current_user, alert.ward_number, staff_db)

    # 5. State transition
    alert.status = "Resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()

    # 6. Structured Security & Operations Audit Logging
    # Log in Database A (Auth/Security audit)
    auth_audit = AuthAuditLog(
        user_id=current_user.id,
        action=f"alert_resolved:{alert.alert_code or alert.id}"
    )
    user_db.add(auth_audit)
    user_db.commit()

    # Log in Database B (Staff operational audit) if user has staff profile
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if staff_profile:
        staff_audit = StaffAuditLog(
            staff_id=staff_profile.id,
            action="alert_resolved",
            performed_by_user_id=current_user.id,
            details=f"Resolved alert {alert.alert_code} for {alert.location_name}"
        )
        staff_db.add(staff_audit)
        staff_db.commit()

    return {
        "success": True,
        "message": f"Alert {alert.alert_code} successfully resolved.",
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "resolved_by": current_user.email,
        "resolved_at": alert.resolved_at.isoformat()
    }
