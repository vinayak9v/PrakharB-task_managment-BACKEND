"""
APScheduler — runs background cron jobs.
- Daily morning to-do for Prakhar Sir
- EOD reminders
- EOD summary at night
- Overdue task escalation check
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def job_send_eod_reminders():
    """Send EOD reminders to non-submitters."""
    logger.info("[CRON] Sending EOD reminders...")
    from app.db.session import SessionLocal
    from app.models.models import User, EODReport, UserRole
    from app.services.whatsapp_service import send_whatsapp_message, eod_reminder_message
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()
        submitted_ids = {r.user_id for r in db.query(EODReport).filter(EODReport.report_date == today).all()}
        pending = db.query(User).filter(
            User.is_active == True,
            User.role == UserRole.TEAM_MEMBER,
            User.id.notin_(submitted_ids)
        ).all()
        for member in pending:
            msg = eod_reminder_message(name=member.name, deadline="6:00 PM")
            await send_whatsapp_message(member.phone, msg)
        logger.info(f"[CRON] EOD reminders sent to {len(pending)} members")
    finally:
        db.close()


async def job_eod_summary():
    """Send EOD summary to Prakhar Sir."""
    logger.info("[CRON] Sending EOD summary to admin...")
    from app.db.session import SessionLocal
    from app.models.models import User, EODReport, Task, TaskStatus, UserRole
    from app.services.whatsapp_service import send_whatsapp_message, daily_summary_message
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()
        all_members = db.query(User).filter(
            User.is_active == True, User.role == UserRole.TEAM_MEMBER
        ).all()
        submitted = db.query(EODReport).filter(EODReport.report_date == today).all()
        submitted_ids = {r.user_id for r in submitted}
        not_submitted = [m for m in all_members if m.id not in submitted_ids]

        completed = db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
        pending = db.query(Task).filter(Task.status.in_([
            TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.WAITING
        ])).count()
        delayed = db.query(Task).filter(Task.status == TaskStatus.DELAYED).count()

        names = "\n".join([f"{i+1}. {m.name}" for i, m in enumerate(not_submitted)]) or "All submitted ✅"
        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        if admin:
            msg = daily_summary_message(
                total=len(all_members),
                submitted=len(submitted),
                not_submitted=len(not_submitted),
                completed_tasks=completed,
                pending_tasks=pending,
                delayed_tasks=delayed,
                not_submitted_names=names
            )
            await send_whatsapp_message(admin.phone, msg)
    finally:
        db.close()


async def job_daily_todo():
    """Generate and send daily to-do to Prakhar Sir."""
    logger.info("[CRON] Generating daily to-do...")
    from app.db.session import SessionLocal
    from app.models.models import User, Task, Meeting, TaskStatus, UserRole, EscalationLevel
    from app.services.whatsapp_service import send_whatsapp_message
    from app.services.ai_service import generate_daily_todo
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()
        overdue = db.query(Task).filter(
            Task.due_date < today, Task.status != TaskStatus.COMPLETED, Task.is_deleted == False
        ).all()
        todays_tasks = db.query(Task).filter(
            Task.due_date == today, Task.is_deleted == False
        ).all()
        meetings = db.query(Meeting).filter(Meeting.meeting_date == today).all()
        escalated = db.query(Task).filter(Task.escalation_level != None).all()

        context = {
            "overdue_tasks": [t.title for t in overdue[:10]],
            "todays_tasks": [t.title for t in todays_tasks[:10]],
            "pending_decisions": [t.title for t in escalated[:5]],
            "meetings": [m.title for m in meetings],
            "eod_non_submitters": []
        }

        summary = await generate_daily_todo(context)
        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        if admin:
            await send_whatsapp_message(admin.phone, summary)
    finally:
        db.close()


async def job_check_overdue_escalation():
    """Auto-check overdue tasks and escalate."""
    logger.info("[CRON] Checking overdue tasks for escalation...")
    from app.db.session import SessionLocal
    from app.models.models import Task, TaskStatus
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()
        overdue_tasks = db.query(Task).filter(
            Task.due_date < today,
            Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.DELAYED]),
            Task.is_deleted == False
        ).all()

        for task in overdue_tasks:
            task.status = TaskStatus.DELAYED
            db.commit()
    finally:
        db.close()


def start_scheduler():
    """Register all cron jobs and start scheduler."""
    eod_time = settings.EOD_REMINDER_TIME.split(":")
    summary_time = settings.EOD_SUMMARY_TIME.split(":")
    todo_time = settings.DAILY_TODO_TIME.split(":")

    # Daily to-do at 7:00 AM
    scheduler.add_job(
        job_daily_todo, CronTrigger(hour=int(todo_time[0]), minute=int(todo_time[1]))
    )

    # EOD reminder at 5:45 PM
    scheduler.add_job(
        job_send_eod_reminders, CronTrigger(hour=int(eod_time[0]), minute=int(eod_time[1]))
    )

    # EOD summary at 7:00 PM
    scheduler.add_job(
        job_eod_summary, CronTrigger(hour=int(summary_time[0]), minute=int(summary_time[1]))
    )

    # Overdue check every hour
    scheduler.add_job(job_check_overdue_escalation, CronTrigger(minute=0))

    scheduler.start()
    logger.info("✅ Scheduler started with all cron jobs")
