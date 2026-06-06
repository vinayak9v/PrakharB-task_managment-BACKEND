from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import Project, ProjectMember, User, UserRole
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectMemberAdd
from app.core.dependencies import get_current_user, require_super_admin, require_admin_or_above
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── CREATE PROJECT ────────────────────────────────────────────────────────────
@router.post("/", response_model=ProjectOut)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    project = Project(
        name            = body.name,
        description     = body.description,
        project_head_id = body.project_head_id,
        created_by      = current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ── LIST PROJECTS — sab roles handle karta hai ───────────────────────────────
@router.get("/", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Super Admin & Admin — sab projects
    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return (
            db.query(Project)
            .order_by(Project.created_at.desc())
            .all()
        )

    # Project Head & Department Head — sirf apne assigned projects
    if current_user.role in [UserRole.PROJECT_HEAD, UserRole.DEPARTMENT_HEAD]:
        return (
            db.query(Project)
            .filter(Project.project_head_id == current_user.id)
            .order_by(Project.created_at.desc())
            .all()
        )

    # Team Member — project_members table se
    memberships = (
        db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )
    project_ids = [m.project_id for m in memberships]
    return (
        db.query(Project)
        .filter(Project.id.in_(project_ids))
        .order_by(Project.created_at.desc())
        .all()
    )


# ── GET PROJECT BY ID ─────────────────────────────────────────────────────────
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── UPDATE PROJECT ────────────────────────────────────────────────────────────
@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


# ── ADD MEMBER ────────────────────────────────────────────────────────────────
@router.post("/{project_id}/members")
def add_member(
    project_id: int,
    body: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(ProjectMember).filter_by(
        project_id=project_id,
        user_id=body.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already in project")

    member = ProjectMember(project_id=project_id, user_id=body.user_id)
    db.add(member)
    db.commit()
    return {"message": f"{user.name} added to {project.name}"}


# ── LIST MEMBERS ──────────────────────────────────────────────────────────────
@router.get("/{project_id}/members")
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    members = (
        db.query(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    return [
        {
            "user_id": u.id,
            "name":    u.name,
            "role":    u.role,
            "phone":   u.phone,
        }
        for _, u in members
    ]