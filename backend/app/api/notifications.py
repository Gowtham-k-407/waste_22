from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_waste_db
from app.models.complaint import Notification
from app.models.user import User
from app.core.security import get_current_user_optional, get_current_user

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])

@router.get("")
def get_notifications(
    role: Optional[str] = Query(None),
    ward_id: Optional[int] = Query(None),
    limit: int = Query(30, le=100),
    waste_db: Session = Depends(get_waste_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = waste_db.query(Notification)

    # Filter based on authenticated user or explicit role/ward parameters
    if current_user:
        user_role = current_user.role
        query = query.filter(
            (Notification.recipient_user_id == current_user.id) |
            (Notification.recipient_role == user_role) |
            (Notification.recipient_role == None)
        )
    elif role:
        query = query.filter(
            (Notification.recipient_role == role) |
            (Notification.recipient_role == None)
        )

    if ward_id:
        query = query.filter((Notification.ward_id == ward_id) | (Notification.ward_id == None))

    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    unread_count = sum(1 for n in notifications if not n.is_read)

    return {
        "unread_count": unread_count,
        "total_count": len(notifications),
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "notification_type": n.notification_type,
                "recipient_role": n.recipient_role,
                "ward_id": n.ward_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "reference_id": n.reference_id
            }
            for n in notifications
        ]
    }

@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    waste_db: Session = Depends(get_waste_db)
):
    notif = waste_db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notif.is_read = True
    waste_db.commit()
    return {"success": True, "notification_id": notification_id, "is_read": True}

@router.post("/mark-all-read")
def mark_all_notifications_read(
    role: Optional[str] = Query(None),
    waste_db: Session = Depends(get_waste_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = waste_db.query(Notification).filter(Notification.is_read == False)
    if current_user:
        query = query.filter(
            (Notification.recipient_user_id == current_user.id) |
            (Notification.recipient_role == current_user.role)
        )
    elif role:
        query = query.filter(Notification.recipient_role == role)

    query.update({"is_read": True}, synchronize_session=False)
    waste_db.commit()
    return {"success": True, "message": "All notifications marked as read."}
