from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.models import UserRole


# ─── Create User ─────────────────────────────────────────────────────────────

class DepartmentInfo(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    password: str
    role: UserRole = UserRole.TEAM_MEMBER

    # Foreign Key
    department_id: Optional[int] = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v):
        v = v.strip().replace(" ", "").replace("-", "")

        if not v.isdigit():
            raise ValueError("Phone must contain only digits")

        if len(v) < 10:
            raise ValueError("Phone must be at least 10 digits")

        return v


# ─── Update User ─────────────────────────────────────────────────────────────

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

    # Changed from department -> department_id
    department_id: Optional[int] = None

    is_active: Optional[bool] = None


# ─── User Output ─────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]

    role: UserRole

    # Changed from department -> department_id
    department: Optional[DepartmentInfo] = None   # ← yeh add karo

    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# ─── Login ───────────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    phone: str
    password: str


# ─── JWT Token Response ──────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    user: UserOut


# ─── Change Password ─────────────────────────────────────────────────────────

class ChangePassword(BaseModel):
    old_password: str
    new_password: str