"""
APScheduler — runs background cron jobs.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from datetime import datetime
import logging

logger    = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


# ── JOB 1 — Daily To-Do 7:00 AM ──────────────────────────────────────────────
async def job_daily_todo():
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
            Task.due_date < today,
            Task.status   != TaskStatus.COMPLETED,
            Task.is_deleted == False
        ).all()

        todays_tasks = db.query(Task).filter(
            Task.due_date   == today,
            Task.is_deleted == False
        ).all()

        meetings = db.query(Meeting).filter(
            Meeting.meeting_date == today
        ).all()

        escalated = db.query(Task).filter(
            Task.escalation_level != None
        ).all()

        context = {
            "overdue_tasks":       [t.title for t in overdue[:10]],
            "todays_tasks":        [t.title for t in todays_tasks[:10]],
            "pending_decisions":   [t.title for t in escalated[:5]],
            "meetings":            [m.title for m in meetings],
            "eod_non_submitters":  []
        }

        summary = await generate_daily_todo(context)

        admin = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()
        if admin:
            await send_whatsapp_message(admin.phone, summary)

    except Exception as e:
        logger.error(f"[CRON] Daily todo error: {e}")
    finally:
        db.close()


# ── JOB 2 — EOD Reminder 5:45 PM ─────────────────────────────────────────────
async def job_send_eod_reminders():
    logger.info("[CRON] Sending EOD reminders...")
    from app.db.session import SessionLocal
    from app.models.models import User, EODReport, UserRole
    from app.services.whatsapp_service import send_whatsapp_message, eod_reminder_message
    from datetime import date

    db = SessionLocal()
    try:
        today        = date.today()
        submitted_ids = {
            r.user_id for r in db.query(EODReport).filter(
                EODReport.report_date == today
            ).all()
        }

        pending = db.query(User).filter(
            User.is_active == True,
            User.role      == UserRole.TEAM_MEMBER,
            User.id.notin_(submitted_ids)
        ).all()

        for member in pending:
            msg = eod_reminder_message(name=member.name, deadline="6:00 PM")
            await send_whatsapp_message(member.phone, msg)

        logger.info(f"[CRON] EOD reminders sent to {len(pending)} members")

    except Exception as e:
        logger.error(f"[CRON] EOD reminder error: {e}")
    finally:
        db.close()


# ── JOB 3 — Evening Report 6:00 PM ───────────────────────────────────────────
async def job_evening_report():
    logger.info("[CRON] Sending 6 PM evening report...")
    from app.db.session import SessionLocal
    from app.models.models import User, EODReport, Task, TaskStatus, UserRole
    from app.services.whatsapp_service import send_whatsapp_message
    from datetime import date, timedelta

    db = SessionLocal()
    try:
        today    = date.today()
        tomorrow = today + timedelta(days=1)

        # EOD status
        all_members = db.query(User).filter(
            User.is_active == True,
            User.role      == UserRole.TEAM_MEMBER
        ).all()

        submitted_today = db.query(EODReport).filter(
            EODReport.report_date == today
        ).all()
        submitted_ids = {r.user_id for r in submitted_today}

        submitted_members     = [m for m in all_members if m.id in submitted_ids]
        not_submitted_members = [m for m in all_members if m.id not in submitted_ids]

        # Tasks
        due_today = db.query(Task).filter(
            Task.due_date   == today,
            Task.status.notin_([TaskStatus.COMPLETED]),
            Task.is_deleted == False
        ).all()

        due_tomorrow = db.query(Task).filter(
            Task.due_date   == tomorrow,
            Task.status.notin_([TaskStatus.COMPLETED]),
            Task.is_deleted == False
        ).all()

        overdue_tasks = db.query(Task).filter(
            Task.due_date   < today,
            Task.status.notin_([TaskStatus.COMPLETED]),
            Task.is_deleted == False
        ).all()

        delayed_tasks = db.query(Task).filter(
            Task.status     == TaskStatus.DELAYED,
            Task.is_deleted == False
        ).all()

        # Message build karo
        submitted_str = "\n".join(
            [f"  ✅ {m.name}" for m in submitted_members]
        ) or "  Kisi ne submit nahi kiya"

        not_submitted_str = "\n".join(
            [f"  ❌ {m.name}" for m in not_submitted_members]
        ) or "  Sab ne submit kar diya ✅"

        due_today_str = "\n".join(
            [f"  ⏰ {t.title} — User #{t.assigned_to_id}"
             for t in due_today[:8]]
        ) or "  Koi task due nahi"

        due_tomorrow_str = "\n".join(
            [f"  📅 {t.title} — User #{t.assigned_to_id}"
             for t in due_tomorrow[:8]]
        ) or "  Koi task due nahi"

        overdue_str = "\n".join(
            [f"  🔴 {t.title} (Due: {t.due_date}) — User #{t.assigned_to_id}"
             for t in overdue_tasks[:8]]
        ) or "  Koi overdue task nahi ✅"

        delayed_str = "\n".join(
            [f"  🚨 {t.title} — User #{t.assigned_to_id}"
             for t in delayed_tasks[:5]]
        ) or "  Koi delayed task nahi ✅"

        msg = f"""📊 Shaam ki Report — {today.strftime('%d %B %Y')}

━━━━━━━━━━━━━━━━━━━━━
📝 EOD REPORT STATUS
━━━━━━━━━━━━━━━━━━━━━
👥 Total Members : {len(all_members)}
✅ Submitted     : {len(submitted_members)}
❌ Not Submitted : {len(not_submitted_members)}

✅ Submitted Members:
{submitted_str}

❌ Not Submitted Members:
{not_submitted_str}

━━━━━━━━━━━━━━━━━━━━━
⏰ TASKS — AAJ KI DEADLINE
━━━━━━━━━━━━━━━━━━━━━
{due_today_str}

━━━━━━━━━━━━━━━━━━━━━
📅 TASKS — KAL KI DEADLINE
━━━━━━━━━━━━━━━━━━━━━
{due_tomorrow_str}

━━━━━━━━━━━━━━━━━━━━━
🔴 OVERDUE TASKS
━━━━━━━━━━━━━━━━━━━━━
{overdue_str}

━━━━━━━━━━━━━━━━━━━━━
🚨 DELAYED TASKS
━━━━━━━━━━━━━━━━━━━━━
{delayed_str}

━━━━━━━━━━━━━━━━━━━━━
📈 SUMMARY
━━━━━━━━━━━━━━━━━━━━━
Aaj Due    : {len(due_today)} tasks
Kal Due    : {len(due_tomorrow)} tasks
Overdue    : {len(overdue_tasks)} tasks
Delayed    : {len(delayed_tasks)} tasks

– AI-PS System"""

        # Super Admin + Admin sab ko bhejo
        admins = db.query(User).filter(
            User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN]),
            User.is_active == True
        ).all()

        for admin in admins:
            await send_whatsapp_message(admin.phone, msg)
            logger.info(
                f"[CRON] Evening report sent to {admin.name} ({admin.phone})"
            )

    except Exception as e:
        logger.error(f"[CRON] Evening report error: {e}")
    finally:
        db.close()


# ── JOB 4 — EOD Summary 7:00 PM ──────────────────────────────────────────────
async def job_eod_summary():
    logger.info("[CRON] Sending EOD summary to admin...")
    from app.db.session import SessionLocal
    from app.models.models import User, EODReport, Task, TaskStatus, UserRole
    from app.services.whatsapp_service import send_whatsapp_message, daily_summary_message
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()

        all_members = db.query(User).filter(
            User.is_active == True,
            User.role      == UserRole.TEAM_MEMBER
        ).all()

        submitted    = db.query(EODReport).filter(
            EODReport.report_date == today
        ).all()
        submitted_ids = {r.user_id for r in submitted}
        not_submitted = [m for m in all_members if m.id not in submitted_ids]

        completed = db.query(Task).filter(
            Task.status == TaskStatus.COMPLETED
        ).count()
        pending   = db.query(Task).filter(
            Task.status.in_([
                TaskStatus.NOT_STARTED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.WAITING
            ])
        ).count()
        delayed   = db.query(Task).filter(
            Task.status == TaskStatus.DELAYED
        ).count()

        names = "\n".join(
            [f"{i+1}. {m.name}" for i, m in enumerate(not_submitted)]
        ) or "All submitted ✅"

        admin = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()

        if admin:
            msg = daily_summary_message(
                total               = len(all_members),
                submitted           = len(submitted),
                not_submitted       = len(not_submitted),
                completed_tasks     = completed,
                pending_tasks       = pending,
                delayed_tasks       = delayed,
                not_submitted_names = names
            )
            await send_whatsapp_message(admin.phone, msg)

    except Exception as e:
        logger.error(f"[CRON] EOD summary error: {e}")
    finally:
        db.close()


# ── JOB 5 — Overdue Check Har Ghante ─────────────────────────────────────────
async def job_check_overdue_escalation():
    logger.info("[CRON] Checking overdue tasks...")
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

        logger.info(
            f"[CRON] {len(overdue_tasks)} tasks marked as delayed"
        )

    except Exception as e:
        logger.error(f"[CRON] Overdue check error: {e}")
    finally:
        db.close()


# ── START SCHEDULER ───────────────────────────────────────────────────────────
def start_scheduler():
    eod_time     = settings.EOD_REMINDER_TIME.split(":")
    summary_time = settings.EOD_SUMMARY_TIME.split(":")
    todo_time    = settings.DAILY_TODO_TIME.split(":")

    # Job 1 — Daily to-do 7:00 AM
    scheduler.add_job(
        job_daily_todo,
        CronTrigger(hour=int(todo_time[0]), minute=int(todo_time[1]))
    )

    # Job 2 — EOD reminder 5:45 PM
    scheduler.add_job(
        job_send_eod_reminders,
        CronTrigger(hour=int(eod_time[0]), minute=int(eod_time[1]))
    )

    # Job 3 — Evening report 6:00 PM
    scheduler.add_job(
        job_evening_report,
        CronTrigger(hour=18, minute=0)
    )

    # Job 4 — EOD summary 7:00 PM
    scheduler.add_job(
        job_eod_summary,
        CronTrigger(hour=int(summary_time[0]), minute=int(summary_time[1]))
    )

    # Job 5 — Overdue check har ghante
    scheduler.add_job(
        job_check_overdue_escalation,
        CronTrigger(minute=0)
    )

    scheduler.start()
    logger.info("✅ Scheduler started — 5 cron jobs active")