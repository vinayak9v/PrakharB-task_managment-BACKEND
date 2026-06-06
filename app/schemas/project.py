from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.models import ProjectStatus
from app.schemas.user import UserOut



class ProjectHeadInfo(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_head_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_head_id: Optional[int] = None
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: ProjectStatus
    project_head_id: Optional[int]
    created_at: datetime
    project_head:    Optional[ProjectHeadInfo] = None 

    model_config = {"from_attributes": True}


class ProjectMemberAdd(BaseModel):
    user_id: int


class ProjectMemberOut(BaseModel):
    user_id: int
    name: str
    role: str

    model_config = {"from_attributes": True}
