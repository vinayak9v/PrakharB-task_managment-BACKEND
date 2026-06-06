"""
Scheduler Test APIs — Manually trigger cron jobs for testing.
SIRF TESTING KE LIYE — Production mein remove kar do.
"""

from fastapi import APIRouter, Depends
from app.core.dependencies import require_super_admin
from app.models.models import User

router = APIRouter(prefix="/scheduler-test", tags=["Scheduler Test"])


@router.post("/evening-report")
async def test_evening_report(
    current_user: User = Depends(require_super_admin)
):
    """6 PM Evening Report manually trigger karo."""
    from app.services.scheduler import job_evening_report
    await job_evening_report()
    return {"message": "Evening report job triggered ✅"}


@router.post("/eod-reminders")
async def test_eod_reminders(
    current_user: User = Depends(require_super_admin)
):
    """5:45 PM EOD reminder manually trigger karo."""
    from app.services.scheduler import job_send_eod_reminders
    await job_send_eod_reminders()
    return {"message": "EOD reminder job triggered ✅"}


@router.post("/daily-todo")
async def test_daily_todo(
    current_user: User = Depends(require_super_admin)
):
    """7 AM Daily to-do manually trigger karo."""
    from app.services.scheduler import job_daily_todo
    await job_daily_todo()
    return {"message": "Daily todo job triggered ✅"}


@router.post("/eod-summary")
async def test_eod_summary(
    current_user: User = Depends(require_super_admin)
):
    """7 PM EOD summary manually trigger karo."""
    from app.services.scheduler import job_eod_summary
    await job_eod_summary()
    return {"message": "EOD summary job triggered ✅"}


@router.post("/overdue-check")
async def test_overdue_check(
    current_user: User = Depends(require_super_admin)
):
    """Overdue task check manually trigger karo."""
    from app.services.scheduler import job_check_overdue_escalation
    await job_check_overdue_escalation()
    return {"message": "Overdue check job triggered ✅"}


@router.get("/status")
async def scheduler_status(
    current_user: User = Depends(require_super_admin)
):
    """Scheduler ka status aur next run time dekho."""
    from app.services.scheduler import scheduler

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "job_id":   job.id,
            "name":     job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else "Not scheduled",
        })

    return {
        "scheduler_running": scheduler.running,
        "total_jobs":        len(jobs),
        "jobs":              jobs
    }