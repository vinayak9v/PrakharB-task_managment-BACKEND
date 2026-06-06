from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.models.models import Notification, User, Task, TaskStatus, UserRole
from app.core.dependencies import get_current_user, require_admin_or_above
from app.services.whatsapp_service import (
    send_whatsapp_message, task_reminder_message, eod_reminder_message
)
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class BroadcastRequest(BaseModel):
    message: str
    user_ids: Optional[List[int]] = None  # None = all active users


@router.post("/broadcast")
async def broadcast_message(
    body: BroadcastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    """Send a WhatsApp broadcast to selected or all users."""
    if body.user_ids:
        users = db.query(User).filter(User.id.in_(body.user_ids), User.is_active == True).all()
    else:
        users = db.query(User).filter(User.is_active == True).all()

    sent, failed = 0, 0
    for user in users:
        result = await send_whatsapp_message(user.phone, body.message)
        if result.get("status") == "error":
            failed += 1
        else:
            sent += 1

    return {"sent": sent, "failed": failed, "total": len(users)}


@router.post("/send-eod-reminders")
async def send_eod_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    """Send EOD reminder to all team members who haven't submitted today."""
    today = date.today()
    from app.models.models import EODReport
    submitted_ids = {
        r.user_id for r in db.query(EODReport).filter(EODReport.report_date == today).all()
    }
    pending_members = db.query(User).filter(
        User.is_active == True,
        User.role == UserRole.TEAM_MEMBER,
        User.id.notin_(submitted_ids)
    ).all()

    sent = 0
    for member in pending_members:
        msg = eod_reminder_message(name=member.name, deadline="6:00 PM")
        await send_whatsapp_message(member.phone, msg)
        sent += 1

    return {"message": f"EOD reminders sent to {sent} members"}


@router.post("/send-task-reminders")
async def send_task_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    """Send reminders for all pending/overdue tasks."""
    from datetime import datetime
    today = date.today()

    pending_tasks = db.query(Task).filter(
        Task.due_date <= today,
        Task.status.notin_([TaskStatus.COMPLETED]),
        Task.is_deleted == False
    ).all()

    sent = 0
    for task in pending_tasks:
        assignee = db.query(User).filter(User.id == task.assigned_to_id).first()
        if assignee:
            from app.models.models import Project
            project = db.query(Project).filter(Project.id == task.project_id).first()
            msg = task_reminder_message(
                name=assignee.name,
                task=task.title,
                project=project.name if project else "N/A",
                deadline=str(task.due_date)
            )
            await send_whatsapp_message(assignee.phone, msg)
            sent += 1

    return {"message": f"Task reminders sent for {sent} tasks"}


@router.get("/history")
def get_notification_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    return db.query(Notification).order_by(
        Notification.created_at.desc()
    ).limit(limit).all()
