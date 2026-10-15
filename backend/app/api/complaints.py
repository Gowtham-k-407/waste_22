import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_waste_db, get_user_db
from app.models.complaint import PublicComplaint, ComplaintFollowUp, Notification
from app.models.user import User
from app.core.security import get_current_user_optional, get_current_user

router = APIRouter(prefix="/complaints", tags=["Public Complaints & Grievance Redressal"])

# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------
class ComplaintCreate(BaseModel):
    category: str = Field(..., description="missed_collection, overflowing_bin, illegal_dumping, drainage_leakage, drainage_blockage, street_cleaning, damaged_bin, other")
    description: str
    location_address: str
    ward_id: int
    zone_number: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_evidence_url: Optional[str] = None
    priority: Optional[str] = "medium" # low, medium, high, critical
    reporter_name: Optional[str] = "Anonymous Resident"
    reporter_phone: Optional[str] = None
    reporter_email: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str = Field(..., description="submitted, under_review, assigned, in_progress, resolved, closed, reopened")
    officer_notes: Optional[str] = None
    resolution_evidence_url: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    assigned_department: Optional[str] = "Solid Waste Management"

class FollowUpCreate(BaseModel):
    message: str
    attachment_url: Optional[str] = None

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
def submit_complaint(
    payload: ComplaintCreate,
    waste_db: Session = Depends(get_waste_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Submits a new public sanitation grievance to Greater Chennai Corporation.
    Generates a unique tracking number (e.g. GCC-GRV-2026-XXXXX).
    """
    tracking = f"GCC-GRV-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    user_id = current_user.id if current_user else None
    reporter_email = current_user.email if current_user else payload.reporter_email
    reporter_name = current_user.full_name if current_user else payload.reporter_name

    complaint = PublicComplaint(
        tracking_number=tracking,
        category=payload.category,
        description=payload.description,
        location_address=payload.location_address,
        ward_id=payload.ward_id,
        zone_number=payload.zone_number or ((payload.ward_id - 1) // 14 + 1),
        latitude=payload.latitude or 13.0827,
        longitude=payload.longitude or 80.2707,
        photo_evidence_url=payload.photo_evidence_url,
        priority=payload.priority or "medium",
        status="submitted",
        reporter_user_id=user_id,
        reporter_name=reporter_name,
        reporter_phone=payload.reporter_phone,
        reporter_email=reporter_email,
        assigned_department="Solid Waste Management",
        data_source="citizen_grievance_portal",
        is_simulated=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    waste_db.add(complaint)
    waste_db.flush()

    # Automatically trigger in-app notification for Ward Sanitary Inspector
    notif = Notification(
        recipient_role="Sanitary Inspector",
        ward_id=payload.ward_id,
        title=f"New Grievance in Ward {payload.ward_id}: {payload.category.replace('_', ' ').title()}",
        message=f"Complaint #{tracking} submitted at {payload.location_address}. Priority: {payload.priority.upper()}.",
        notification_type="complaint_filed",
        reference_id=complaint.id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    waste_db.add(notif)
    waste_db.commit()
    waste_db.refresh(complaint)

    return {
        "success": True,
        "tracking_number": complaint.tracking_number,
        "complaint_id": complaint.id,
        "status": complaint.status,
        "message": f"Grievance recorded successfully. Reference tracking number: {complaint.tracking_number}",
        "ward_id": complaint.ward_id,
        "estimated_sla_hours": 24 if complaint.priority in ("critical", "high") else 48
    }

@router.get("")
def list_complaints(
    ward_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    waste_db: Session = Depends(get_waste_db)
):
    query = waste_db.query(PublicComplaint)
    if ward_id:
        query = query.filter(PublicComplaint.ward_id == ward_id)
    if status:
        query = query.filter(PublicComplaint.status == status)
    if category:
        query = query.filter(PublicComplaint.category == category)

    complaints = query.order_by(PublicComplaint.created_at.desc()).limit(limit).all()
    return {
        "count": len(complaints),
        "complaints": [
            {
                "id": c.id,
                "tracking_number": c.tracking_number,
                "category": c.category,
                "description": c.description,
                "location_address": c.location_address,
                "ward_id": c.ward_id,
                "zone_number": c.zone_number,
                "priority": c.priority,
                "status": c.status,
                "reporter_name": c.reporter_name,
                "assigned_officer_name": c.assigned_officer_name,
                "assigned_worker_name": c.assigned_worker_name,
                "photo_evidence_url": c.photo_evidence_url,
                "resolution_evidence_url": c.resolution_evidence_url,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "is_simulated": c.is_simulated
            }
            for c in complaints
        ]
    }

@router.get("/{tracking_or_id}")
def get_complaint_details(
    tracking_or_id: str,
    waste_db: Session = Depends(get_waste_db)
):
    if tracking_or_id.isdigit():
        complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == int(tracking_or_id)).first()
    else:
        complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.tracking_number == tracking_or_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Grievance not found with provided tracking ID.")

    follow_ups = waste_db.query(ComplaintFollowUp).filter(
        ComplaintFollowUp.complaint_id == complaint.id
    ).order_by(ComplaintFollowUp.created_at.asc()).all()

    return {
        "complaint": {
            "id": complaint.id,
            "tracking_number": complaint.tracking_number,
            "category": complaint.category,
            "description": complaint.description,
            "location_address": complaint.location_address,
            "ward_id": complaint.ward_id,
            "zone_number": complaint.zone_number,
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "priority": complaint.priority,
            "status": complaint.status,
            "reporter_name": complaint.reporter_name,
            "reporter_phone": complaint.reporter_phone,
            "assigned_department": complaint.assigned_department,
            "assigned_officer_name": complaint.assigned_officer_name,
            "assigned_worker_name": complaint.assigned_worker_name,
            "photo_evidence_url": complaint.photo_evidence_url,
            "resolution_evidence_url": complaint.resolution_evidence_url,
            "resolution_notes": complaint.resolution_notes,
            "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "data_source": complaint.data_source,
            "is_simulated": complaint.is_simulated
        },
        "timeline": [
            {
                "id": f.id,
                "author_name": f.author_name,
                "author_role": f.author_role,
                "message": f.message,
                "attachment_url": f.attachment_url,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in follow_ups
        ]
    }

@router.post("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    payload: StatusUpdate,
    waste_db: Session = Depends(get_waste_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authorized municipal workflow to advance grievance resolution lifecycle.
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
    complaint.status = payload.status
    complaint.updated_at = datetime.utcnow()

    if payload.officer_notes:
        complaint.resolution_notes = payload.officer_notes
    if payload.resolution_evidence_url:
        complaint.resolution_evidence_url = payload.resolution_evidence_url
    if payload.assigned_worker_name:
        complaint.assigned_worker_name = payload.assigned_worker_name
    if payload.assigned_department:
        complaint.assigned_department = payload.assigned_department

    if payload.status in ("resolved", "closed"):
        complaint.resolved_at = datetime.utcnow()

    # Log timeline note
    note = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_name=current_user.full_name,
        author_role=current_user.role,
        message=f"Status updated from '{old_status}' to '{payload.status}'. Notes: {payload.officer_notes or 'None'}",
        attachment_url=payload.resolution_evidence_url,
        created_at=datetime.utcnow()
    )
    waste_db.add(note)

    # In-app notification for citizen / reporter if registered
    if complaint.reporter_user_id:
        notif = Notification(
            recipient_user_id=complaint.reporter_user_id,
            title=f"Update on Complaint #{complaint.tracking_number}",
            message=f"Your grievance status has been updated to '{payload.status.replace('_', ' ').title()}'.",
            notification_type="complaint_resolved" if payload.status == "resolved" else "complaint_updated",
            reference_id=complaint.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        waste_db.add(notif)

    waste_db.commit()
    return {
        "success": True,
        "complaint_id": complaint.id,
        "tracking_number": complaint.tracking_number,
        "status": complaint.status,
        "message": f"Grievance status updated to {complaint.status}."
    }

@router.post("/{complaint_id}/follow-up")
def add_follow_up(
    complaint_id: int,
    payload: FollowUpCreate,
    waste_db: Session = Depends(get_waste_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    name = current_user.full_name if current_user else "Resident Follow-up"
    role = current_user.role if current_user else "Resident"

    follow_up = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_name=name,
        author_role=role,
        message=payload.message,
        attachment_url=payload.attachment_url,
        created_at=datetime.utcnow()
    )
    waste_db.add(follow_up)
    complaint.updated_at = datetime.utcnow()
    waste_db.commit()

    return {"success": True, "message": "Follow-up added to complaint timeline."}

@router.post("/{complaint_id}/reopen")
def reopen_complaint(
    complaint_id: int,
    reason: str = Query(..., min_length=5),
    waste_db: Session = Depends(get_waste_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    complaint = waste_db.query(PublicComplaint).filter(PublicComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    complaint.status = "reopened"
    complaint.updated_at = datetime.utcnow()

    name = current_user.full_name if current_user else "Resident"
    note = ComplaintFollowUp(
        complaint_id=complaint.id,
        author_name=name,
        author_role=current_user.role if current_user else "Resident",
        message=f"Grievance reopened by resident. Reason: {reason}",
        created_at=datetime.utcnow()
    )
    waste_db.add(note)
    waste_db.commit()

    return {
        "success": True,
        "tracking_number": complaint.tracking_number,
        "status": "reopened",
        "message": "Grievance has been reopened and queued for supervisor inspection."
    }
