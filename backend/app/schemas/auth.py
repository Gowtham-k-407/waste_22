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

class UserAdminDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    organization: Optional[str] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    email_verified: bool
    must_change_password: bool = False
    contribution_points: int = 0
    badges: str = "Eco Citizen"
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    assigned_ward: Optional[int] = None
    staff_profile: Optional[dict] = None

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    items: List[UserAdminDetailResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class UserRoleUpdateRequest(BaseModel):
    role: str
    reason: Optional[str] = None

class RoleDefinitionResponse(BaseModel):
    role: str
    title: str
    department: str
    scope: Optional[str] = None
    description: Optional[str] = None
    is_staff: bool = False
    is_admin: bool = False

class UserAdminCreateRequest(BaseModel):
    full_name: str
    email: str
    username: Optional[str] = None
    role: str = "contributor"
    organization: Optional[str] = None
    city: Optional[str] = "Chennai"
    phone_number: Optional[str] = None
    assigned_ward: Optional[int] = None
    is_active: bool = True
    employee_id: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None

class UserAdminCreateResponse(BaseModel):
    success: bool
    message: str
    user: UserAdminDetailResponse
    activation_token: Optional[str] = None
    activation_url: Optional[str] = None
    email_delivery_status: str

class UserAdminUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    assigned_ward: Optional[int] = None
    is_active: Optional[bool] = None

class AdminPasswordResetResponse(BaseModel):
    success: bool
    message: str
    user_id: int
    email: str
    reset_token: Optional[str] = None
    reset_url: Optional[str] = None
    email_delivery_status: str