"""
Daily To-Do API for Prakhar Sir.
Fetches all pending data from DB and generates AI-powered priority list.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime
from app.db.session import get_db
from app.models.models import (
    Task, User, Meeting, EODReport,
    TaskStatus, UserRole, EscalationLevel
)
from app.core.dependencies import require_super_admin
from app.services.ai_servicee import generate_daily_todo
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter(prefix="/daily-todo", tags=["Daily To-Do"])


@router.post("/generate")
async def generate_daily_todo_api(
    send_whatsapp: bool = False,          # ?send_whatsapp=true → WA par bhi bhejo
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Generate AI-powered daily to-do list for Prakhar Sir.
    Checks: pending tasks, today's meetings, overdue work,
            team follow-ups, EOD reports, decisions pending,
            project priorities.
    """
    today      = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    # ── 1. Overdue Tasks ─────────────────────────────────────────────────────
    overdue_tasks = db.query(Task).filter(
        Task.due_date < today,
        Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.DELAYED]),
        Task.is_deleted == False
    ).order_by(Task.due_date.asc()).all()

    # ── 2. Today's Tasks ─────────────────────────────────────────────────────
    todays_tasks = db.query(Task).filter(
        Task.due_date == today,
        Task.status.notin_([TaskStatus.COMPLETED]),
        Task.is_deleted == False
    ).order_by(Task.priority.desc()).all()

    # ── 3. Today's Meetings ──────────────────────────────────────────────────
    todays_meetings = db.query(Meeting).filter(
        Meeting.meeting_date == today
    ).all()

    # ── 4. Escalated / Decision Pending Tasks ────────────────────────────────
    pending_decisions = db.query(Task).filter(
        Task.escalation_level == EscalationLevel.LEVEL_3,
        Task.status != TaskStatus.COMPLETED,
        Task.is_deleted == False
    ).all()

    # ── 5. Delayed Tasks ─────────────────────────────────────────────────────
    delayed_tasks = db.query(Task).filter(
        Task.status == TaskStatus.DELAYED,
        Task.is_deleted == False
    ).all()

    # ── 6. Yesterday EOD Non-Submitters ─────────────────────────────────────
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    all_members = db.query(User).filter(
        User.is_active == True,
        User.role == UserRole.TEAM_MEMBER
    ).all()
    submitted_yesterday = {
        r.user_id for r in db.query(EODReport).filter(
            EODReport.report_date == yesterday
        ).all()
    }
    eod_non_submitters = [
        m for m in all_members if m.id not in submitted_yesterday
    ]

    # ── 7. High Priority Pending Tasks ───────────────────────────────────────
    high_priority = db.query(Task).filter(
        Task.priority == "high",
        Task.status.notin_([TaskStatus.COMPLETED]),
        Task.is_deleted == False
    ).all()

    # ── Build context for AI ─────────────────────────────────────────────────
    context = {
        "today": str(today),
        "overdue_tasks": [
            {
                "title":       t.title,
                "project_id":  t.project_id,
                "due_date":    str(t.due_date),
                "assigned_to": t.assigned_to_id,
                "priority":    t.priority,
            }
            for t in overdue_tasks[:10]
        ],
        "todays_tasks": [
            {
                "title":    t.title,
                "priority": t.priority,
                "status":   t.status,
            }
            for t in todays_tasks[:10]
        ],
        "todays_meetings": [
            {
                "title": m.title,
                "time":  str(m.meeting_time) if m.meeting_time else "Time not set",
            }
            for m in todays_meetings
        ],
        "pending_decisions": [
            {
                "title":      t.title,
                "project_id": t.project_id,
            }
            for t in pending_decisions[:5]
        ],
        "delayed_tasks": [
            {
                "title":        t.title,
                "delay_reason": t.delay_reason or "No reason provided",
            }
            for t in delayed_tasks[:8]
        ],
        "eod_non_submitters": [m.name for m in eod_non_submitters],
        "high_priority_tasks": [
            {
                "title":  t.title,
                "status": t.status,
            }
            for t in high_priority[:5]
        ],
    }

    # ── Generate AI Summary ──────────────────────────────────────────────────
    ai_summary = await generate_daily_todo(context)

    # ── Optionally send on WhatsApp ──────────────────────────────────────────
    whatsapp_sent = False
    if send_whatsapp:
        admin = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()
        if admin:
            await send_whatsapp_message(admin.phone, ai_summary)
            whatsapp_sent = True

    # ── Return full response ─────────────────────────────────────────────────
    return {
        "ai_summary": ai_summary,
        "whatsapp_sent": whatsapp_sent,
        "data": {
            "overdue_tasks_count":    len(overdue_tasks),
            "todays_tasks_count":     len(todays_tasks),
            "meetings_today":         len(todays_meetings),
            "pending_decisions":      len(pending_decisions),
            "delayed_tasks":          len(delayed_tasks),
            "eod_non_submitters":     len(eod_non_submitters),
            "high_priority_pending":  len(high_priority),
        }
    }