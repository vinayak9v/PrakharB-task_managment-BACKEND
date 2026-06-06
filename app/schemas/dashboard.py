from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DashboardSummary(BaseModel):
    total_tasks_today: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    high_priority_tasks: int
    eod_submitted: int
    eod_not_submitted: int
    meetings_today: int
    pending_decisions: int
    escalated_tasks: int


class ProjectSummary(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    completed: int
    pending: int
    delayed: int
    completion_percentage: float


class DelayedTask(BaseModel):
    task_id: int
    task_title: str
    project_name: str
    assigned_to: str
    due_date: date
    escalation_level: Optional[str]
    delay_reason: Optional[str]


class DashboardFull(BaseModel):
    summary: DashboardSummary
    project_summaries: List[ProjectSummary]
    delayed_tasks: List[DelayedTask]
    todays_meetings: List[dict]
