from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str
    full_name: str
    role: str = "contributor"
    organization: Optional[str] = "Resident Contributor"
    city: Optional[str] = "Chennai"

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    organization: Optional[str] = "Resident Contributor"
    city: Optional[str] = "Chennai"

class UserLogin(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None
    city: Optional[str] = None
    assigned_ward: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    organization: Optional[str] = None
    city: Optional[str] = None
    assigned_ward: Optional[int] = None
    profile_image: Optional[str] = None
    is_active: bool
    contribution_points: int
    badges: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class RoleSwitchRequest(BaseModel):
    role: str

class ContributorStatsResponse(BaseModel):
    total_contributions: int
    validated_contributions: int
    pending_contributions: int
    rejected_contributions: int
    user_corrections: int
    eco_points: int
    badges: List[str]
    recent_uploads: List[Any] = []