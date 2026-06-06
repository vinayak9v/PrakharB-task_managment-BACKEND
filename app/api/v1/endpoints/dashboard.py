from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from app.db.session import get_db
from app.models.models import (
    Task, User, Project, Meeting, EODReport,
    TaskStatus, UserRole, EscalationLevel
)
from app.schemas.dashboard import DashboardSummary, ProjectSummary, DelayedTask, DashboardFull
from app.core.dependencies import get_current_user, require_admin_or_above

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardFull)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    now = datetime.utcnow()

    # ── Task Stats ─────────────────────────────────
    base_query = db.query(Task).filter(Task.is_deleted == False)

    if current_user.role == UserRole.TEAM_MEMBER:
        base_query = base_query.filter(Task.assigned_to_id == current_user.id)

    all_tasks = base_query.all()
    today_tasks = [t for t in all_tasks if t.due_date == today]
    completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
    pending = [t for t in all_tasks if t.status in [
        TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.WAITING
    ]]
    overdue = [t for t in all_tasks if t.due_date < today and t.status != TaskStatus.COMPLETED]
    high_priority = [t for t in all_tasks if t.priority.value == "high" and t.status != TaskStatus.COMPLETED]
    escalated = [t for t in all_tasks if t.escalation_level is not None]
    delayed = [t for t in all_tasks if t.status == TaskStatus.DELAYED]

    # ── EOD Stats ──────────────────────────────────
    all_members = db.query(User).filter(
        User.is_active == True, User.role == UserRole.TEAM_MEMBER
    ).count()
    submitted_eod = db.query(EODReport).filter(
        EODReport.report_date == today
    ).count()

    # ── Today's Meetings ───────────────────────────
    todays_meetings = db.query(Meeting).filter(Meeting.meeting_date == today).all()

    # ── Summary ────────────────────────────────────
    summary = DashboardSummary(
        total_tasks_today=len(today_tasks),
        completed_tasks=len(completed),
        pending_tasks=len(pending),
        overdue_tasks=len(overdue),
        high_priority_tasks=len(high_priority),
        eod_submitted=submitted_eod,
        eod_not_submitted=max(0, all_members - submitted_eod),
        meetings_today=len(todays_meetings),
        pending_decisions=len(escalated),
        escalated_tasks=len(escalated)
    )

    # ── Project Summaries ──────────────────────────
    projects = db.query(Project).all()
    project_summaries = []
    for p in projects:
        p_tasks = [t for t in all_tasks if t.project_id == p.id]
        total = len(p_tasks)
        if total == 0:
            continue
        comp = len([t for t in p_tasks if t.status == TaskStatus.COMPLETED])
        pend = len([t for t in p_tasks if t.status != TaskStatus.COMPLETED])
        dly = len([t for t in p_tasks if t.status == TaskStatus.DELAYED])
        project_summaries.append(ProjectSummary(
            project_id=p.id,
            project_name=p.name,
            total_tasks=total,
            completed=comp,
            pending=pend,
            delayed=dly,
            completion_percentage=round((comp / total) * 100, 1)
        ))

    # ── Delayed Tasks Detail ───────────────────────
    delayed_detail = []
    for t in delayed[:20]:  # top 20
        assignee = db.query(User).filter(User.id == t.assigned_to_id).first()
        project = db.query(Project).filter(Project.id == t.project_id).first()
        delayed_detail.append(DelayedTask(
            task_id=t.id,
            task_title=t.title,
            project_name=project.name if project else "N/A",
            assigned_to=assignee.name if assignee else "N/A",
            due_date=t.due_date,
            escalation_level=t.escalation_level.value if t.escalation_level else None,
            delay_reason=t.delay_reason
        ))

    return DashboardFull(
        summary=summary,
        project_summaries=project_summaries,
        delayed_tasks=delayed_detail,
        todays_meetings=[
            {"id": m.id, "title": m.title, "project_id": m.project_id,
             "time": str(m.meeting_time) if m.meeting_time else "N/A"}
            for m in todays_meetings
        ]
    )


@router.get("/project/{project_id}")
def get_project_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    tasks = db.query(Task).filter(
        Task.project_id == project_id, Task.is_deleted == False
    ).all()

    return {
        "project_id": project_id,
        "total_tasks": len(tasks),
        "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        "not_started": len([t for t in tasks if t.status == TaskStatus.NOT_STARTED]),
        "delayed": len([t for t in tasks if t.status == TaskStatus.DELAYED]),
        "overdue": len([t for t in tasks if t.due_date < today and t.status != TaskStatus.COMPLETED]),
    }
