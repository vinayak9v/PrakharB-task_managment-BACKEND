# app/api/v1/endpoints/performance.py

"""
User Performance API
- Phone number se user dhundo
- Weekly / Monthly / Yearly performance report
- Task completion rate, delays, EOD compliance, meeting attendance
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
from typing import Optional
from app.db.session import get_db
from app.models.models import (
    Task, User, EODReport, Meeting,
    TaskStatus, UserRole
)
from app.core.dependencies import require_admin_or_above

router = APIRouter(prefix="/performance", tags=["Performance"])


# ─── Helper — Date Range Calculate ───────────────────────────────────────────

def get_date_range(period: str, year: int, month: int = None, week: int = None):
    """
    period = 'week' | 'month' | 'year'
    Returns (start_date, end_date)
    """
    if period == "year":
        return date(year, 1, 1), date(year, 12, 31)

    if period == "month":
        if month is None:
            raise HTTPException(status_code=400, detail="month required for monthly report")
        # Last day of month
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return date(year, month, 1), end

    if period == "week":
        if week is None:
            raise HTTPException(status_code=400, detail="week number required for weekly report")
        # ISO week number se start/end nikalo
        start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w").date()
        end   = start + timedelta(days=6)
        return start, end

    raise HTTPException(status_code=400, detail="period must be: week | month | year")


# ─── Helper — Task Stats ──────────────────────────────────────────────────────

def get_task_stats(db, user_id: int, start: date, end: date) -> dict:
    """User ke tasks ka stats nikalo given date range mein."""

    all_tasks = db.query(Task).filter(
        Task.assigned_to_id == user_id,
        Task.due_date >= start,
        Task.due_date <= end,
        Task.is_deleted == False
    ).all()

    completed       = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
    delayed         = [t for t in all_tasks if t.status == TaskStatus.DELAYED]
    not_started     = [t for t in all_tasks if t.status == TaskStatus.NOT_STARTED]
    in_progress     = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]

    # On-time completed — completed_at <= due_date
    on_time = [
        t for t in completed
        if t.completed_at and t.completed_at.date() <= t.due_date
    ]

    # Late completed — completed_at > due_date
    late_completed = [
        t for t in completed
        if t.completed_at and t.completed_at.date() > t.due_date
    ]

    total = len(all_tasks)
    completion_rate = round((len(completed) / total * 100), 1) if total > 0 else 0
    on_time_rate    = round((len(on_time) / len(completed) * 100), 1) if completed else 0
    delay_rate      = round((len(delayed) / total * 100), 1) if total > 0 else 0

    return {
        "total_assigned":    total,
        "completed":         len(completed),
        "delayed":           len(delayed),
        "not_started":       len(not_started),
        "in_progress":       len(in_progress),
        "on_time_completed": len(on_time),
        "late_completed":    len(late_completed),
        "completion_rate":   completion_rate,   # % tasks completed
        "on_time_rate":      on_time_rate,       # % completed on time
        "delay_rate":        delay_rate,         # % tasks delayed
        "tasks_detail": [
            {
                "id":           t.id,
                "title":        t.title,
                "project_id":   t.project_id,
                "priority":     t.priority,
                "status":       t.status,
                "due_date":     str(t.due_date),
                "completed_at": str(t.completed_at.date()) if t.completed_at else None,
                "on_time":      (
                    t.completed_at.date() <= t.due_date
                    if t.completed_at else None
                ),
                "delay_reason": t.delay_reason,
            }
            for t in all_tasks
        ]
    }


# ─── Helper — EOD Stats ───────────────────────────────────────────────────────

def get_eod_stats(db, user_id: int, start: date, end: date) -> dict:
    """EOD submission compliance check karo."""

    # Total working days (Mon-Fri) in range
    total_working_days = sum(
        1 for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5   # 0-4 = Mon-Fri
    )

    submitted_reports = db.query(EODReport).filter(
        EODReport.user_id == user_id,
        EODReport.report_date >= start,
        EODReport.report_date <= end
    ).order_by(EODReport.report_date.desc()).all()

    submitted_count  = len(submitted_reports)
    missed_count     = max(0, total_working_days - submitted_count)
    compliance_rate  = round((submitted_count / total_working_days * 100), 1) if total_working_days > 0 else 0

    return {
        "total_working_days":  total_working_days,
        "submitted":           submitted_count,
        "missed":              missed_count,
        "compliance_rate":     compliance_rate,    # % EOD submit kiye
        "reports": [
            {
                "date":             str(r.report_date),
                "completed_work":   r.completed_work,
                "pending_work":     r.pending_work,
                "delay_reason":     r.delay_reason,
                "tomorrow_plan":    r.tomorrow_plan,
                "support_required": r.support_required,
                "submitted_at":     str(r.submitted_at),
            }
            for r in submitted_reports
        ]
    }


# ─── Helper — Performance Score ───────────────────────────────────────────────

def calculate_score(task_stats: dict, eod_stats: dict) -> dict:
    """
    Overall performance score 0-100 calculate karo.

    Weightage:
    - Task Completion Rate : 40%
    - On-Time Rate         : 35%
    - EOD Compliance       : 25%
    """
    task_score  = task_stats["completion_rate"] * 0.40
    ontime_score = task_stats["on_time_rate"]   * 0.35
    eod_score   = eod_stats["compliance_rate"]  * 0.25

    total_score = round(task_score + ontime_score + eod_score, 1)

    # Grade
    if total_score >= 90:
        grade, label = "A+", "Excellent"
    elif total_score >= 80:
        grade, label = "A",  "Very Good"
    elif total_score >= 70:
        grade, label = "B",  "Good"
    elif total_score >= 60:
        grade, label = "C",  "Average"
    elif total_score >= 50:
        grade, label = "D",  "Below Average"
    else:
        grade, label = "F",  "Poor"

    return {
        "overall_score":  total_score,
        "grade":          grade,
        "label":          label,
        "breakdown": {
            "task_completion_score": round(task_score, 1),
            "on_time_score":         round(ontime_score, 1),
            "eod_compliance_score":  round(eod_score, 1),
        }
    }


# ─── MAIN API ─────────────────────────────────────────────────────────────────

@router.get("/by-phone")
def get_user_performance(
    phone:  str            = Query(..., description="User ka phone number, e.g. 919876543210"),
    period: str            = Query(..., description="week | month | year"),
    year:   int            = Query(default=None),
    month:  Optional[int]  = Query(default=None, description="1-12, for monthly report"),
    week:   Optional[int]  = Query(default=None, description="1-52, for weekly report"),
    db:     Session        = Depends(get_db),
    current_user: User     = Depends(require_admin_or_above)
):
    """
    Phone number se user ka performance report nikalo.

    Examples:
      Weekly  : ?phone=919876543210&period=week&year=2025&week=3
      Monthly : ?phone=919876543210&period=month&year=2025&month=1
      Yearly  : ?phone=919876543210&period=year&year=2025
    """

    # ── Default year = current year ──────────────────────────────────────────
    if year is None:
        year = date.today().year

    # ── 1. User dhundo ───────────────────────────────────────────────────────
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Koi user nahi mila is phone number se: {phone}"
        )

    # ── 2. Date range nikalo ─────────────────────────────────────────────────
    start_date, end_date = get_date_range(period, year, month, week)

    # ── 3. Stats nikalo ──────────────────────────────────────────────────────
    task_stats = get_task_stats(db, user.id, start_date, end_date)
    eod_stats  = get_eod_stats(db, user.id, start_date, end_date)
    score      = calculate_score(task_stats, eod_stats)

    # ── 4. Response ──────────────────────────────────────────────────────────
    return {
        "user": {
            "id":         user.id,
            "name":       user.name,
            "phone":      user.phone,
            "email":      user.email,
            "role":       user.role,
            "is_active":  user.is_active,
        },
        "report_period": {
            "period":     period,
            "year":       year,
            "month":      month,
            "week":       week,
            "start_date": str(start_date),
            "end_date":   str(end_date),
        },
        "performance_score": score,
        "task_performance":  task_stats,
        "eod_compliance":    eod_stats,
    }