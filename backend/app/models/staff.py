from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from app.core.database import StaffBase

class StaffProfile(StaffBase):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False) # Stable link to User in Database A
    employee_id = Column(String, unique=True, index=True, nullable=False) # e.g. GCC-EMP-1001
    full_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False, index=True) # One of the 35 municipal roles
    role_code = Column(String, nullable=False, index=True) # standardized role slug
    department = Column(String, nullable=False, index=True)
    
    # Geographic & Facility Scopes
    assigned_zone_id = Column(Integer, nullable=True)
    assigned_zone_number = Column(Integer, nullable=True, index=True)
    assigned_ward_id = Column(Integer, nullable=True)
    assigned_ward_number = Column(Integer, nullable=True, index=True)
    assigned_facility_id = Column(Integer, nullable=True)
    assigned_facility_name = Column(String, nullable=True)
    
    # Fleet & Route Assignments
    assigned_vehicle_id = Column(Integer, nullable=True)
    assigned_vehicle_code = Column(String, nullable=True)
    assigned_route = Column(String, nullable=True)
    
    # Hierarchy & Shifts
    supervisor_id = Column(Integer, nullable=True) # Links to supervisor's StaffProfile.id
    shift = Column(String, default="Morning (06:00 - 14:00)")
    
    # Contact & Status
    phone_number = Column(String, nullable=False)
    emergency_contact = Column(String, nullable=True)
    employment_status = Column(String, default="Active", index=True) # Active, On Leave, Suspended, Transferred
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StaffDutyAssignment(StaffBase):
    __tablename__ = "staff_duty_assignments"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, index=True, nullable=False)
    duty_date = Column(DateTime, default=datetime.utcnow, index=True)
    shift = Column(String, default="Morning (06:00 - 14:00)")
    task_description = Column(Text, nullable=False)
    ward_number = Column(Integer, nullable=True)
    facility_name = Column(String, nullable=True)
    status = Column(String, default="Assigned", index=True) # Assigned, In Progress, Completed, Reassigned
    completion_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StaffAuditLog(StaffBase):
    __tablename__ = "staff_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, index=True, nullable=False)
    action = Column(String, nullable=False) # profile_created, duty_assigned, status_changed, role_updated
    performed_by_user_id = Column(Integer, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
