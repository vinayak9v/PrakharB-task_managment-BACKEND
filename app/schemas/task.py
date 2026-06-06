from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time
from app.models.models import TaskPriority, TaskStatus, EscalationLevel


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: int
    assigned_to_id: int
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date
    due_time: Optional[time] = None
    remarks: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    remarks: Optional[str] = None
    assigned_to_id: Optional[int]          = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    delay_reason: Optional[str] = None
    remarks: Optional[str] = None


class TaskFollowUpCreate(BaseModel):
    note: str


class TaskFollowUpOut(BaseModel):
    id: int
    note: str
    updated_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    project_id: int
    assigned_to_id: int
    assigned_by_id: int
    priority: TaskPriority
    status: TaskStatus
    due_date: date
    due_time: Optional[time]
    delay_reason: Optional[str]
    remarks: Optional[str]
    escalation_level: Optional[EscalationLevel]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TaskOutDetail(TaskOut):
    follow_ups: List[TaskFollowUpOut] = []
