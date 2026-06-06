from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.db.session import get_db
from app.models.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return current_user


def require_admin_or_above(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PROJECT_HEAD, UserRole.DEPARTMENT_HEAD]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_project_head_or_above(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PROJECT_HEAD]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Project Head access required")
    return current_user
