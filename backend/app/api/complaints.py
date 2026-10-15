import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_waste_db, get_user_db, get_staff_db
from app.models.complaint import PublicComplaint, ComplaintFollowUp, Notification, GCC_ESCALATION_HIERARCHY
from app.models.user import User
from app.models.staff import StaffProfile
from app.core.security import get_current_user_from_token
from app.core.rbac import ADMIN_ROLES, MUNICIPAL_STAFF_ROLES

router = APIRouter(prefix="/complaints", tags=["Public Complaints & Grievance Redressal"])

ALLOWED_CATEGORIES = {
    "missed_collection",
    "overflowing_bin",
    "illegal_dumping",
    "drainage_leakage",
    "drainage_blockage",
    "street_cleaning",
    "damaged_bin",
    "public_sanitation_hazard",
    "other"
}

# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------
class ComplaintCreate(BaseModel):
    title: Optional[str] = None
    category: str = Field(..., description="missed_collection, overflowing_bin, illegal_dumping, drainage_leakage, drainage_blockage, street_cleaning, damaged_bin, public_sanitation_hazard, other")
    description: str = Field(..., min_length=10, max_length=2000)
    location_address: str = Field(..., min_length=5, max_length=300)
    ward_id: Optional[int] = None
    zone_number: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_evidence_url: Optional[str] = None
    priority: Optional[str] = "Medium"
    reporter_phone: Optional[str] = None

class StatusUpdate(BaseModel):
    status: Optional[str] = Field(None, description="submitted, under_review, assigned, in_progress, resolved, closed, reopened")
    new_status: Optional[str] = None
    notes: Optional[str] = None
    officer_notes: Optional[str] = None
    resolution_evidence_url: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    assigned_department: Optional[str] = "Solid Waste Management"

class ReopenRequest(BaseModel):
    reason: Optional[str] = None

class FollowUpCreate(BaseModel):
    message: str = Field(..., min_length=5, max_length=1500)
    attachment_url: Optional[str] = None

class EscalationRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for escalating this grievance")

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
def submit_complaint(
    payload: ComplaintCreate,
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Submits a new public sanitation grievance to Greater Chennai Corporation.
    Associates the report strictly with the authenticated resident and generates a unique tracking code.
    Client-supplied status, assigned worker, or resolution fields are ignored.
    """
    cat = payload.category.strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{payload.category}'. Supported categories: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    # Ward resolution: if payload specifies a valid ward (1-200), use it; otherwise bind to user's registered area
    if payload.ward_id and 1 <= payload.ward_id <= 200:
        ward_num = payload.ward_id
    else:
        ward_num = current_user.assigned_ward

    zone_num = payload.zone_number or ((ward_num - 1) // 14 + 1)
    tracking = f"GCC-SAN-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

    initial_history = [
        {
            "status": "submitted",
            "timestamp": datetime.utcnow().isoformat(),
            "updated_by": current_user.full_name,
            "escalation_tier": 0,
            "notes": "Sanitation grievance registered by resident."
        }
    ]

    complaint = PublicComplaint(
        complaint_code=tracking,
        category=cat,
        description=payload.description.strip(),
        location_name=payload.location_address.strip(),
        ward_number=ward_num,
        zone_number=zone_num,
        latitude=payload.latitude or 13.0827,
        longitude=payload.longitude or 80.2707,
        evidence_image_url=payload.photo_evidence_url,
        priority=payload.priority.capitalize() if payload.priority else "Medium",
        status="submitted",
        status_history_json=json.dumps(initial_history),
        citizen_user_id=current_user.id,
        citizen_name=current_user.full_name,
        citizen_phone=payload.reporter_phone or current_user.phone_number,
        citizen_email=current_user.email,
        assigned_department="Ward Sanitation Office",
        assigned_staff_name="Ward Sanitary Inspector",
        data_source="citizen_portal",
        is_simulated=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    waste_db.add(complaint)
    waste_db.flush()

    # Create in-app operational notification for the Ward Sanitary Inspector
    notif = Notification(
        recipient_role="Sanitary Inspector",
        target_ward_number=ward_num,
        target_department="Ward Sanitation Office",
        title=f"New Grievance in Ward {ward_num}: {cat.replace('_', ' ').title()}",
        message=f"Grievance #{tracking} filed at {payload.location_address}. Priority: {complaint.priority}.",
        category="Grievance",
        priority="High" if complaint.priority in ("Critical", "High") else "Normal",
        link_url=f"/alerts",
        is_read=False,
        created_at=datetime.utcnow()
    )
    waste_db.add(notif)
    waste_db.commit()
    waste_db.refresh(complaint)

    return {
        "success": True,
        "id": complaint.id,
        "complaint_id": complaint.id,
        "complaint_code": complaint.complaint_code,
        "tracking_number": complaint.complaint_code,
        "title": payload.title or complaint.title,
        "category": complaint.category,
        "status": complaint.status,
        "priority": complaint.priority,
        "citizen_user_id": complaint.citizen_user_id,
        "ward_number": complaint.ward_number,
        "ward_id": complaint.ward_number,
        "assigned_department": complaint.assigned_department,
        "assigned_authority": complaint.assigned_staff_name,
        "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
        "estimated_sla_hours": complaint.sla_hours,
        "message": f"Sanitation grievance recorded successfully. Reference tracking number: {complaint.complaint_code}"
    }

@router.get("")
def list_complaints(
    ward_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    waste_db: Session = Depends(get_waste_db),
    staff_db: Session = Depends(get_staff_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Lists complaints according to strict authorization boundaries:
    - Ordinary public and contributor users can ONLY list complaints they personally reported.
    - Ward-scoped municipal staff can only list complaints within their assigned ward.
    - System admins and higher commissioners can view city-wide complaints.
    """
    query = waste_db.query(PublicComplaint)

    if current_user.role in ["public", "contributor"]:
        # Hard ownership filter: ordinary users CANNOT view other people's complaints
        query = query.filter(PublicComplaint.citizen_user_id == current_user.id)
    else:
        # Staff role scoping
        if current_user.role not in ADMIN_ROLES and current_user.role != "municipal_commissioner":
            staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
            if staff_profile and staff_profile.assigned_ward_number:
                query = query.filter(PublicComplaint.ward_number == staff_profile.assigned_ward_number)
            elif ward_id:
                query = query.filter(PublicComplaint.ward_number == ward_id)
        elif ward_id:
            query = query.filter(PublicComplaint.ward_number == ward_id)

    if status_filter:
        query = query.filter(PublicComplaint.status == status_filter)
    if category:
        query = query.filter(PublicComplaint.category == category)

    complaints = query.order_by(PublicComplaint.created_at.desc()).limit(limit).all()

    return {
        "count": len(complaints),
        "complaints": [
            {
                "id": c.id,
                "complaint_code": c.complaint_code,
                "tracking_number": c.complaint_code,
                "category": c.category,
                "description": c.description,
                "location_address": c.location_name,
                "ward_id": c.ward_number,
                "zone_number": c.zone_number,
                "priority": c.priority,
                "status": c.status,
                "assigned_department": c.assigned_department,
                "assigned_authority": c.assigned_staff_name,
                "current_escalation_tier": c.current_escalation_tier,
                "can_escalate": c.is_escalation_eligible if current_user.role in ["public", "contributor"] else False,
                "photo_evidence_url": c.evidence_image_url,
                "resolution_notes": c.resolution_notes,
                "resolution_evidence_url": c.resolution_evidence_url,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "estimated_sla_hours": c.sla_hours,
                "is_simulated": c.is_simulated
            }
            for c in complaints
        ]
    }

@router.get("/{tracking_or_id}")
def get_complaint_details(
    tracking_or_id: str,
    waste_db: Session = Depends(get_waste_db),
    staff_db: Session = Depends(get_staff_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Retrieves full details of a single grievance including resolution timeline.
    Enforces object-level ownership: public users receive 404 if the complaint is not theirs.
    """
    if tracking_or_id.isdigit():
        complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == int(tracking_or_id)).first()
    else:
        complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.complaint_code == tracking_or_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Grievance not found.")

    # Object-level authorization check
    if current_user.role in ["public", "contributor"]:
        if complaint.citizen_user_id != current_user.id:
            # Return 404 to prevent resource enumeration
            raise HTTPException(status_code=404, detail="Grievance not found.")
    elif current_user.role not in ADMIN_ROLES and current_user.role != "municipal_commissioner":
        staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if staff_profile and staff_profile.assigned_ward_number and complaint.ward_number != staff_profile.assigned_ward_number:
            raise HTTPException(status_code=404, detail="Grievance not found within your operational ward.")

    follow_ups = waste_db.query(ComplaintFollowUp).filter(
        ComplaintFollowUp.complaint_id == complaint.id
    ).order_by(ComplaintFollowUp.created_at.asc()).all()

    # Parse status history
    history = []
    if complaint.status_history_json:
        try:
            history = json.loads(complaint.status_history_json)
        except Exception:
            history = []

    return {
        "complaint": {
            "id": complaint.id,
            "complaint_code": complaint.complaint_code,
            "tracking_number": complaint.complaint_code,
            "category": complaint.category,
            "description": complaint.description,
            "location_address": complaint.location_name,
            "ward_id": complaint.ward_number,
            "zone_number": complaint.zone_number,
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "priority": complaint.priority,
            "status": complaint.status,
            "assigned_department": complaint.assigned_department,
            "assigned_authority": complaint.assigned_staff_name,
            "current_escalation_tier": complaint.current_escalation_tier,
            "can_escalate": complaint.is_escalation_eligible,
            "photo_evidence_url": complaint.evidence_image_url,
            "resolution_evidence_url": complaint.resolution_evidence_url,
            "resolution_notes": complaint.resolution_notes,
            "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "estimated_sla_hours": complaint.sla_hours,
            "data_source": complaint.data_source,
            "is_simulated": complaint.is_simulated
        },
        "status_history": history,
        "timeline": [
            {
                "id": f.id,
                "author_name": f.author_name,
                "author_role": f.author_type,
                "message": f.message,
                "attachment_url": f.evidence_url,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in follow_ups
        ]
    }

@router.post("/{complaint_id}/follow-up")
def add_follow_up(
    complaint_id: int,
    payload: FollowUpCreate,
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Adds citizen follow-up message or supporting photo evidence to their own grievance timeline.
    Staff and admins can also add follow-up notes.
    """
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    if current_user.role in ["public", "contributor"]:
        if complaint.citizen_user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Complaint not found.")

    author_type = "citizen" if current_user.role in ["public", "contributor"] else "staff"

    follow_up = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_type=author_type,
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        message=payload.message.strip(),
        evidence_url=payload.attachment_url,
        created_at=datetime.utcnow()
    )
    waste_db.add(follow_up)
    complaint.updated_at = datetime.utcnow()
    waste_db.commit()

    return {
        "success": True,
        "complaint_id": complaint.id,
        "message": "Follow-up information added to grievance timeline."
    }

@router.post("/{complaint_id}/escalate")
def escalate_complaint(
    complaint_id: int,
    payload: EscalationRequest,
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Escalates an eligible unresolved grievance to the next designated higher municipal authority.
    Citizens can ONLY escalate their own eligible grievances.
    Hierarchy:
      Tier 0: Ward Sanitary Inspector
      Tier 1: Assistant Engineer / Zonal Officer
      Tier 2: Municipal Health Officer
      Tier 3: Municipal Commissioner Executive Cell
    """
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Grievance not found.")

    if current_user.role in ["public", "contributor"]:
        if complaint.citizen_user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Grievance not found.")

    # Validation: Resolved or closed grievances cannot be escalated
    if (complaint.status or "").lower() in ("resolved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot escalate an already resolved or closed grievance. If the issue has resurfaced, please reopen the grievance."
        )

    current_tier = complaint.current_escalation_tier
    if current_tier >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This grievance has already been escalated to the highest municipal authority (Municipal Commissioner Executive Cell)."
        )

    new_tier = current_tier + 1
    target_authority = GCC_ESCALATION_HIERARCHY[new_tier]

    old_dept = complaint.assigned_department
    complaint.assigned_department = target_authority["department"]
    complaint.assigned_staff_name = target_authority["title"]
    complaint.priority = "Critical" if new_tier >= 2 else "High"
    complaint.status = "escalated"
    complaint.updated_at = datetime.utcnow()

    # Append to status history
    history = []
    if complaint.status_history_json:
        try:
            history = json.loads(complaint.status_history_json)
        except Exception:
            history = []

    history.append({
        "status": "escalated",
        "timestamp": datetime.utcnow().isoformat(),
        "escalation_tier": new_tier,
        "escalated_by": current_user.full_name,
        "escalated_to": target_authority["title"],
        "department": target_authority["department"],
        "reason": payload.reason.strip()
    })
    complaint.status_history_json = json.dumps(history)

    # Add timeline entry
    escalation_note = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_type="citizen_escalation",
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        message=f"Grievance escalated to Tier {new_tier} ({target_authority['title']}). Reason: {payload.reason.strip()}",
        created_at=datetime.utcnow()
    )
    waste_db.add(escalation_note)

    # In-app notification for the escalated municipal authority
    notif = Notification(
        recipient_role=target_authority["title"],
        target_ward_number=complaint.ward_number,
        target_department=target_authority["department"],
        title=f"ESCALATION [Tier {new_tier}]: Grievance #{complaint.complaint_code}",
        message=f"Resident escalated {complaint.category.replace('_', ' ').title()} grievance to {target_authority['title']}. Reason: {payload.reason.strip()}",
        category="Grievance",
        priority="Urgent",
        link_url=f"/alerts",
        is_read=False,
        created_at=datetime.utcnow()
    )
    waste_db.add(notif)
    waste_db.commit()
    waste_db.refresh(complaint)

    return {
        "success": True,
        "complaint_id": complaint.id,
        "complaint_code": complaint.complaint_code,
        "status": complaint.status,
        "escalation_tier": new_tier,
        "escalation_level": new_tier,
        "assigned_department": complaint.assigned_department,
        "assigned_authority": complaint.assigned_staff_name,
        "assigned_authority_role": target_authority["title"],
        "priority": complaint.priority,
        "message": f"Grievance successfully escalated to Tier {new_tier}: {target_authority['title']} ({target_authority['department']})."
    }

@router.post("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    payload: StatusUpdate,
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Authorized municipal workflow to advance grievance resolution lifecycle.
    Citizens and ordinary contributors are explicitly denied (HTTP 403).
    """
    if current_user.role in ["public", "contributor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only GCC municipal staff and administrators can update grievance status."
        )

    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    old_status = complaint.status
    target_status = (payload.status or payload.new_status or "in_progress").lower()
    complaint.status = target_status
    complaint.updated_at = datetime.utcnow()

    notes_val = payload.officer_notes or payload.notes or f"Status changed from '{old_status}' to '{target_status}'"
    if notes_val:
        complaint.resolution_notes = notes_val
    if payload.resolution_evidence_url:
        complaint.resolution_evidence_url = payload.resolution_evidence_url
    if payload.assigned_worker_name:
        complaint.assigned_worker_name = payload.assigned_worker_name
    if payload.assigned_department:
        complaint.assigned_department = payload.assigned_department

    if payload.status in ("resolved", "closed"):
        complaint.resolved_at = datetime.utcnow()

    # Append to status history
    history = []
    if complaint.status_history_json:
        try:
            history = json.loads(complaint.status_history_json)
        except Exception:
            history = []

    history.append({
        "status": payload.status,
        "timestamp": datetime.utcnow().isoformat(),
        "updated_by": current_user.full_name,
        "role": current_user.role,
        "notes": payload.officer_notes or f"Status changed from '{old_status}' to '{payload.status}'"
    })
    complaint.status_history_json = json.dumps(history)

    # Log timeline note
    note = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_type="staff",
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        message=f"Status updated from '{old_status}' to '{payload.status}'. Notes: {payload.officer_notes or 'None'}",
        evidence_url=payload.resolution_evidence_url,
        created_at=datetime.utcnow()
    )
    waste_db.add(note)

    # In-app notification for citizen / reporter if registered
    if complaint.citizen_user_id:
        notif = Notification(
            recipient_user_id=complaint.citizen_user_id,
            title=f"Update on Grievance #{complaint.complaint_code}",
            message=f"Your grievance status has been updated to '{payload.status.replace('_', ' ').title()}'.",
            category="Grievance",
            priority="Normal",
            link_url=f"/grievances",
            is_read=False,
            created_at=datetime.utcnow()
        )
        waste_db.add(notif)

    waste_db.commit()
    return {
        "success": True,
        "complaint_id": complaint.id,
        "complaint_code": complaint.complaint_code,
        "status": complaint.status,
        "message": f"Grievance status updated to {complaint.status}."
    }

@router.post("/{complaint_id}/reopen")
def reopen_complaint(
    complaint_id: int,
    payload: Optional[ReopenRequest] = None,
    reason: Optional[str] = Query(None),
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Reopens a resolved or closed grievance if the resident is unsatisfied with the remediation.
    """
    reopen_reason = ((payload.reason if payload and payload.reason else reason) or "").strip()
    if len(reopen_reason) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A substantive reason (at least 5 characters) must be provided to reopen a resolved grievance."
        )

    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    if current_user.role in ["public", "contributor"]:
        if complaint.citizen_user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Complaint not found.")

    if (complaint.status or "").lower() not in ("resolved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only resolved or closed grievances can be reopened. For open grievances, please use the follow-up or escalation feature."
        )

    complaint.status = "reopened"
    complaint.updated_at = datetime.utcnow()

    # Status history
    history = []
    if complaint.status_history_json:
        try:
            history = json.loads(complaint.status_history_json)
        except Exception:
            history = []

    history.append({
        "status": "reopened",
        "timestamp": datetime.utcnow().isoformat(),
        "updated_by": current_user.full_name,
        "notes": f"Reopened by resident: {reason}"
    })
    complaint.status_history_json = json.dumps(history)

    note = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_type="citizen",
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        message=f"Grievance reopened by resident. Reason: {reason}",
        created_at=datetime.utcnow()
    )
    waste_db.add(note)
    waste_db.commit()

    return {
        "success": True,
        "complaint_code": complaint.complaint_code,
        "status": "reopened",
        "message": "Grievance has been reopened and queued for supervisor reinspection."
    }
