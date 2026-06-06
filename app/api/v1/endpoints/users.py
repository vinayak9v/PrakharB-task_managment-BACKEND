from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.models import User, UserRole, AuditLog, Department
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.core.security import get_password_hash
from app.core.dependencies import (
    get_current_user, require_super_admin, require_admin_or_above
)
from app.services.whatsapp_service import send_whatsapp_message, new_account_message
from app.core.config import settings
from datetime import datetime
import secrets

router = APIRouter(prefix="/users", tags=["Users"])


# ── CREATE USER ───────────────────────────────────────────────────────────────
@router.post("/", response_model=UserOut)
async def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    # Role-based creation rules
    if current_user.role == UserRole.PROJECT_HEAD:
        if body.role not in [UserRole.TEAM_MEMBER]:
            raise HTTPException(
                status_code=403,
                detail="Project Head can only create Team Members"
            )

    # Check duplicate phone
    if db.query(User).filter(User.phone == body.phone).first():
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    # Department validate karo
    if body.department_id:
        dept = db.query(Department).filter(
            Department.id == body.department_id
        ).first()
        if not dept:
            raise HTTPException(
                status_code=404,
                detail=f"Department with id {body.department_id} not found"
            )

    raw_password = body.password or secrets.token_urlsafe(8)

    user = User(
        name=body.name,
        phone=body.phone,
        email=body.email,
        hashed_password=get_password_hash(raw_password),
        role=body.role,
        department_id=body.department_id,
        created_by=current_user.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # WhatsApp credentials bhejo
    msg = new_account_message(
        name=user.name,
        phone=user.phone,
        password=raw_password,
        platform_url="http://your-platform-url.com"
    )
    await send_whatsapp_message(user.phone, msg)

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action="user_created",
        module="user",
        detail={"created_user_id": user.id, "role": user.role}
    ))
    db.commit()

    return user


# ── LIST USERS ────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    query = db.query(User)

    # ✅ Department Head — sirf apne department ke users
    if current_user.role == UserRole.DEPARTMENT_HEAD:
        query = query.filter(
            User.department_id == current_user.department_id
        )

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.created_at.desc()).all()


# ── GET SINGLE USER ───────────────────────────────────────────────────────────
@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── UPDATE USER ───────────────────────────────────────────────────────────────
@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


# ── DEACTIVATE USER ───────────────────────────────────────────────────────────
@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"User {user.name} deactivated successfully"}