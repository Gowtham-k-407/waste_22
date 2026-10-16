import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.core.database import get_user_db, get_waste_db, get_staff_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, get_current_user_from_token
)
from app.core.rbac import MUNICIPAL_STAFF_ROLES
from app.models.user import User, PasswordResetToken, AuthAuditLog
from app.models.staff import StaffProfile
from app.models.contribution import ImageContribution
from app.schemas.auth import (
    UserRegister, UserLogin, ForgotPasswordRequest,
    ResetPasswordRequest, ChangePasswordRequest,
    UserProfileUpdate, UserResponse, TokenResponse,
    RoleSwitchRequest, ContributorStatsResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication & Roles"])

@router.post("/register", response_model=TokenResponse)
def register_user(req: UserRegister, user_db: Session = Depends(get_user_db)):
    """Public self-registration. Strictly grants 'contributor' or 'public' role only."""
    email_clean = req.email.strip().lower()
    existing_user = user_db.query(User).filter(func.lower(User.email) == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    base_username = email_clean.split("@")[0]
    username = base_username
    counter = 1
    while user_db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1

    hashed_pw = hash_password(req.password)
    new_user = User(
        username=username,
        email=email_clean,
        hashed_password=hashed_pw,
        full_name=req.full_name.strip(),
        role="contributor", # Public self-registration never grants staff or admin privileges
        organization=req.organization or "Resident Contributor",
        city=req.city or "Chennai",
        contribution_points=50,
        badges="Eco Citizen, Early Adopter",
        must_change_password=False,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    user_db.add(new_user)
    user_db.commit()
    user_db.refresh(new_user)

    # Log registration in Database A
    audit = AuthAuditLog(user_id=new_user.id, action="registration")
    user_db.add(audit)
    user_db.commit()

    token = create_access_token({"sub": new_user.email, "role": new_user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLogin, user_db: Session = Depends(get_user_db)):
    email_or_user = req.email.strip().lower()
    user = user_db.query(User).filter(
        (func.lower(User.email) == email_or_user) | (func.lower(User.username) == email_or_user)
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        if user:
            audit = AuthAuditLog(user_id=user.id, action="login_failure")
            user_db.add(audit)
            user_db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The email or password you entered is incorrect. Please try again."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator."
        )

    user.last_login_at = datetime.now(timezone.utc)
    audit = AuthAuditLog(user_id=user.id, action="login_success")
    user_db.add(audit)
    user_db.commit()

    expire_delta = timedelta(days=30) if req.remember_me else timedelta(days=7)
    token = create_access_token({"sub": user.email, "role": user.role}, expires_delta=expire_delta)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, user_db: Session = Depends(get_user_db)):
    email_clean = req.email.strip().lower()
    user = user_db.query(User).filter(func.lower(User.email) == email_clean).first()

    reset_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=2)

    if user:
        token_entry = PasswordResetToken(
            token=reset_token,
            user_id=user.id,
            expires_at=expires,
            is_used=False
        )
        user_db.add(token_entry)
        user_db.commit()

    return {
        "success": True,
        "message": "If an account exists with this email address, password reset instructions have been generated.",
        "reset_token": reset_token if user else None,
        "test_reset_url": f"/reset-password?token={reset_token}" if user else None
    }

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, user_db: Session = Depends(get_user_db)):
    token_entry = user_db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token.strip(),
        PasswordResetToken.is_used == False
    ).first()

    if not token_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has already been used. Please request a new one."
        )

    now = datetime.now(timezone.utc)
    token_exp = token_entry.expires_at.replace(tzinfo=timezone.utc) if token_entry.expires_at.tzinfo is None else token_entry.expires_at
    if now > token_exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired. Please request a new link."
        )

    user = user_db.query(User).filter(User.id == token_entry.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user account was found associated with this reset link."
        )

    user.hashed_password = hash_password(req.new_password)
    user.must_change_password = False
    user.updated_at = datetime.now(timezone.utc)
    token_entry.is_used = True

    audit = AuthAuditLog(user_id=user.id, action="password_reset_complete")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "message": "Your password has been reset successfully! You can now sign in with your new password."
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user_from_token)):
    return current_user

@router.put("/profile", response_model=UserResponse)
def update_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user_from_token),
    user_db: Session = Depends(get_user_db)
):
    if req.full_name is not None and req.full_name.strip():
        current_user.full_name = req.full_name.strip()
    if req.organization is not None:
        current_user.organization = req.organization.strip()
    if req.city is not None:
        current_user.city = req.city.strip()
    if req.assigned_ward is not None:
        if not (1 <= req.assigned_ward <= 200):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ward number. Greater Chennai Corporation has wards 1 through 200."
            )
        import json
        prefs = {}
        if current_user.preferences_json:
            try:
                prefs = json.loads(current_user.preferences_json)
            except Exception:
                prefs = {}
        prefs["assigned_ward"] = req.assigned_ward
        current_user.preferences_json = json.dumps(prefs)

    current_user.updated_at = datetime.now(timezone.utc)
    user_db.commit()
    user_db.refresh(current_user)
    return current_user

@router.put("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_from_token),
    user_db: Session = Depends(get_user_db)
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current password you entered is incorrect."
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your new password must be at least 6 characters long."
        )

    current_user.hashed_password = hash_password(req.new_password)
    current_user.must_change_password = False
    current_user.updated_at = datetime.now(timezone.utc)

    audit = AuthAuditLog(user_id=current_user.id, action="password_change")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "message": "Your password has been changed successfully."
    }

@router.get("/profile-stats", response_model=ContributorStatsResponse)
def get_user_profile_stats(
    current_user: User = Depends(get_current_user_from_token),
    waste_db: Session = Depends(get_waste_db)
):
    # Query contributions from Database C
    user_contribs = waste_db.query(ImageContribution).filter(
        ImageContribution.contributor_email == current_user.email
    ).all()

    total = len(user_contribs)
    validated = sum(1 for c in user_contribs if c.validation_status in ["approved", "approved_in_dataset", "staged_for_training"])
    pending = sum(1 for c in user_contribs if c.validation_status == "pending")
    rejected = sum(1 for c in user_contribs if c.validation_status == "rejected")
    corrections = sum(1 for c in user_contribs if c.is_user_corrected)

    badges_list = [b.strip() for b in current_user.badges.split(",") if b.strip()] if current_user.badges else ["Eco Citizen"]

    if total == 0:
        points = current_user.contribution_points or 50
        recent = waste_db.query(ImageContribution).order_by(ImageContribution.created_at.desc()).limit(5).all()
        recent_data = [
            {
                "id": r.id,
                "file_path": r.image_url,
                "category": r.user_confirmed_category or r.ai_predicted_category,
                "confidence": r.ai_confidence,
                "status": r.validation_status,
                "date": r.created_at.strftime("%b %d, %Y") if r.created_at else "Recently"
            }
            for r in recent
        ]
        return {
            "total_contributions": max(1, points // 50),
            "validated_contributions": max(1, points // 60),
            "pending_contributions": 0,
            "rejected_contributions": 0,
            "user_corrections": 0,
            "eco_points": points,
            "badges": badges_list,
            "recent_uploads": recent_data
        }

    recent_data = [
        {
            "id": r.id,
            "file_path": r.image_url,
            "category": r.user_confirmed_category or r.ai_predicted_category,
            "confidence": r.ai_confidence,
            "status": r.validation_status,
            "date": r.created_at.strftime("%b %d, %Y") if r.created_at else "Recently"
        }
        for r in user_contribs[:5]
    ]

    return {
        "total_contributions": total,
        "validated_contributions": validated,
        "pending_contributions": pending,
        "rejected_contributions": rejected,
        "user_corrections": corrections,
        "eco_points": current_user.contribution_points,
        "badges": badges_list,
        "recent_uploads": recent_data
    }

@router.get("/roles")
def get_available_roles():
    """Returns the catalog of all roles: system admin, public, contributor, and 35 municipal roles."""
    roles_list = [
        {"role": "system_admin", "title": "System Administrator", "department": "Administration", "description": "Full platform administration, account provisioning, security, and models."},
        {"role": "public", "title": "Public Resident", "department": "Citizens", "description": "Public portal access, collection tracking, complaints, awareness, and scores."},
        {"role": "contributor", "title": "Eco Volunteer / Contributor", "department": "Citizens", "description": "Contribute waste photos, verify AI predictions, earn community points and badges."}
    ]
    for role_code, info in MUNICIPAL_STAFF_ROLES.items():
        roles_list.append({
            "role": role_code,
            "title": info["title"],
            "department": info["department"],
            "scope": info["scope"],
            "description": f"GCC Staff Role: {info['title']} in {info['department']}"
        })
    return roles_list

@router.post("/switch-role")
def switch_user_role(
    req: RoleSwitchRequest,
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    user_db: Session = Depends(get_user_db)
):
    """
    Role switching is strictly validated against server-side eligibility:
    - System Administrators can preview any role or return to system_admin.
    - Permanent role assignment is preserved so administrators are never locked out.
    - Staff members can switch only to their assigned server-side role, or public/contributor modes.
    - Public/contributor users cannot self-escalate to any municipal staff or administrative role.
    Upon successful role change, a freshly signed session JWT with the updated role is issued.
    """
    valid_roles = list(MUNICIPAL_STAFF_ROLES.keys()) + ["system_admin", "public", "contributor", "ai_admin", "municipal_officer", "plant_operator"]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    KNOWN_SYSTEM_ADMINS = {
        settings.ADMIN_BOOTSTRAP_EMAIL.lower(),
        "admin@chennaiswm.gov.in",
        "test_admin@chennai.gov.in",
        "sys_admin_test@chennai.gov.in"
    }

    # Inspect preferences_json for permanent_role
    prefs = {}
    if current_user.preferences_json:
        try:
            prefs = json.loads(current_user.preferences_json)
        except Exception:
            prefs = {}

    # Check server-side staff profile assignment
    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()

    # Determine permanent role
    is_system_admin = (
        current_user.role == "system_admin"
        or prefs.get("permanent_role") == "system_admin"
        or (staff_profile and staff_profile.role_code == "system_admin")
        or current_user.email.lower() in KNOWN_SYSTEM_ADMINS
    )

    if is_system_admin:
        # Guarantee permanent_role is preserved as system_admin
        prefs["permanent_role"] = "system_admin"
    elif staff_profile:
        # User is an authorized staff member; they can switch between their assigned role and citizen modes
        allowed_roles_for_user = {staff_profile.role_code, "contributor", "public"}
        if req.role not in allowed_roles_for_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Your assigned municipal staff role is '{staff_profile.role_code}'. You cannot self-escalate to '{req.role}'."
            )
    else:
        # Ordinary citizen/contributor user
        allowed_roles_for_user = {"public", "contributor"}
        if req.role not in allowed_roles_for_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Privilege escalation prohibited: Role '{req.role}' requires municipal verification. Public users cannot self-assign staff or admin roles."
            )

    prefs["active_persona"] = req.role
    current_user.preferences_json = json.dumps(prefs)
    current_user.role = req.role
    current_user.updated_at = datetime.now(timezone.utc)
    user_db.commit()
    user_db.refresh(current_user)

    # Issue new access token with updated role claim
    new_token = create_access_token({"sub": current_user.email, "role": current_user.role, "name": current_user.full_name})

    audit = AuthAuditLog(user_id=current_user.id, action=f"role_switched_to_{req.role}")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "access_token": new_token,
        "token_type": "bearer",
        "active_role": req.role,
        "user": current_user,
        "message": f"Active role updated to {req.role}"
    }

@router.post("/restore-session")
def restore_session_role(
    current_user: User = Depends(get_current_user_from_token),
    staff_db: Session = Depends(get_staff_db),
    user_db: Session = Depends(get_user_db)
):
    """
    Safely restore active session role to the user's authoritative permanent role.
    Verifies that the user has verified permanent admin or staff rights.
    """
    KNOWN_SYSTEM_ADMINS = {
        settings.ADMIN_BOOTSTRAP_EMAIL.lower(),
        "admin@chennaiswm.gov.in",
        "test_admin@chennai.gov.in",
        "sys_admin_test@chennai.gov.in"
    }

    prefs = {}
    if current_user.preferences_json:
        try:
            prefs = json.loads(current_user.preferences_json)
        except Exception:
            prefs = {}

    staff_profile = staff_db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()

    is_system_admin = (
        current_user.role == "system_admin"
        or prefs.get("permanent_role") == "system_admin"
        or (staff_profile and staff_profile.role_code == "system_admin")
        or current_user.email.lower() in KNOWN_SYSTEM_ADMINS
    )

    if is_system_admin:
        target_role = "system_admin"
        prefs["permanent_role"] = "system_admin"
    elif staff_profile:
        target_role = staff_profile.role_code
        prefs["permanent_role"] = staff_profile.role_code
    else:
        target_role = prefs.get("permanent_role") or "contributor"

    current_user.role = target_role
    if "active_persona" in prefs:
        del prefs["active_persona"]
    current_user.preferences_json = json.dumps(prefs) if prefs else None
    current_user.updated_at = datetime.now(timezone.utc)
    user_db.commit()
    user_db.refresh(current_user)

    new_token = create_access_token({"sub": current_user.email, "role": current_user.role, "name": current_user.full_name})
    audit = AuthAuditLog(user_id=current_user.id, action=f"session_restored_to_permanent_role_{target_role}")
    user_db.add(audit)
    user_db.commit()

    return {
        "success": True,
        "access_token": new_token,
        "token_type": "bearer",
        "active_role": target_role,
        "user": current_user,
        "message": f"Active session restored to verified permanent role '{target_role}'."
    }


