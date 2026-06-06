from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.db.session import get_db
from app.models.models import (
    EODReport, User, Project, ProjectMember,
    UserRole, Task, TaskStatus
)
from app.schemas.meeting_eod import EODCreate, EODOut, EODDailySummary
from app.core.dependencies import get_current_user, require_admin_or_above
from app.services.whatsapp_service import (
    send_whatsapp_message, daily_summary_message
)

router = APIRouter(prefix="/eod", tags=["EOD Reports"])


# ── SUBMIT EOD ────────────────────────────────────────────────────────────────
@router.post("/submit", response_model=EODOut)
def submit_eod(
    body: EODCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()

    # Duplicate check — update karo agar already submit kiya hai
    existing = db.query(EODReport).filter(
        EODReport.user_id    == current_user.id,
        EODReport.project_id == body.project_id,
        EODReport.report_date == today
    ).first()

    if existing:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        existing.submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    report = EODReport(
        user_id          = current_user.id,
        project_id       = body.project_id,
        report_date      = today,
        completed_work   = body.completed_work,
        pending_work     = body.pending_work,
        delay_reason     = body.delay_reason,
        tomorrow_plan    = body.tomorrow_plan,
        support_required = body.support_required,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ── MY REPORTS ────────────────────────────────────────────────────────────────
@router.get("/my-reports", response_model=List[EODOut])
def get_my_reports(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(EODReport).filter(
        EODReport.user_id == current_user.id
    )
    if project_id:
        query = query.filter(EODReport.project_id == project_id)
    return query.order_by(EODReport.report_date.desc()).limit(30).all()


# ── DAILY SUMMARY ─────────────────────────────────────────────────────────────
@router.get("/daily-summary")
def get_daily_summary(
    report_date: Optional[date] = None,
    project_id:  Optional[int]  = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    target_date = report_date or date.today()

    # ✅ Department Head — sirf apne department ke members
    if current_user.role == UserRole.DEPARTMENT_HEAD:
        members_query = db.query(User).filter(
            User.is_active     == True,
            User.role          == UserRole.TEAM_MEMBER,
            User.department_id == current_user.department_id
        )
    else:
        members_query = db.query(User).filter(
            User.is_active == True,
            User.role      == UserRole.TEAM_MEMBER
        )

    all_members = members_query.all()

    # Submitted EODs
    eod_query = db.query(EODReport).filter(
        EODReport.report_date == target_date
    )
    if project_id:
        eod_query = eod_query.filter(
            EODReport.project_id == project_id
        )
    submitted_reports = eod_query.all()
    submitted_ids     = {r.user_id for r in submitted_reports}

    # Not submitted members
    not_submitted = [
        {"user_id": m.id, "name": m.name, "phone": m.phone}
        for m in all_members
        if m.id not in submitted_ids
    ]

    return {
        "date":                  str(target_date),
        "total_members":         len(all_members),
        "submitted_count":       len(submitted_ids),
        "not_submitted_count":   len(not_submitted),
        "not_submitted_members": not_submitted,
        "submitted_reports": [
            {
                "id":              r.id,
                "user_id":         r.user_id,
                "project_id":      r.project_id,
                "report_date":     str(r.report_date),
                "completed_work":  r.completed_work,
                "pending_work":    r.pending_work,
                "delay_reason":    r.delay_reason,
                "tomorrow_plan":   r.tomorrow_plan,
                "support_required":r.support_required,
                "submitted_at":    str(r.submitted_at),
            }
            for r in submitted_reports
        ]
    }


# ── SEND SUMMARY TO ADMIN ─────────────────────────────────────────────────────
@router.post("/send-summary-to-admin")
async def send_eod_summary_to_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    today       = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    # All active team members
    all_members = db.query(User).filter(
        User.is_active == True,
        User.role      == UserRole.TEAM_MEMBER
    ).all()

    # Submitted today
    submitted     = db.query(EODReport).filter(
        EODReport.report_date == today
    ).all()
    submitted_ids = {r.user_id for r in submitted}
    not_submitted = [m for m in all_members if m.id not in submitted_ids]

    # ✅ Task counts — sirf aaj ke completed
    completed = db.query(Task).filter(
        Task.status       == TaskStatus.COMPLETED,
        Task.completed_at >= today_start
    ).count()

    pending = db.query(Task).filter(
        Task.status.in_([
            TaskStatus.NOT_STARTED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.WAITING
        ])
    ).count()

    delayed = db.query(Task).filter(
        Task.status == TaskStatus.DELAYED
    ).count()

    not_submitted_str = "\n".join(
        [f"{i+1}. {m.name}" for i, m in enumerate(not_submitted)]
    ) or "All submitted ✅"

    # Super Admin ko bhejo
    admin = db.query(User).filter(
        User.role == UserRole.SUPER_ADMIN
    ).first()

    if not admin:
        return {"message": "Super Admin not found", "sent": False}

    msg = daily_summary_message(
        total             = len(all_members),
        submitted         = len(submitted),
        not_submitted     = len(not_submitted),
        completed_tasks   = completed,
        pending_tasks     = pending,
        delayed_tasks     = delayed,
        not_submitted_names = not_submitted_str
    )
    await send_whatsapp_message(admin.phone, msg)

    return {
        "message":       "EOD summary sent to admin",
        "sent":          True,
        "total_members": len(all_members),
        "submitted":     len(submitted),
        "not_submitted": len(not_submitted),
    }


# ── NON SUBMITTERS ────────────────────────────────────────────────────────────
@router.get("/non-submitters")
def get_non_submitters(
    report_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    target_date   = report_date or date.today()
    all_members   = db.query(User).filter(
        User.is_active == True,
        User.role      == UserRole.TEAM_MEMBER
    ).all()
    submitted_ids = {
        r.user_id for r in db.query(EODReport).filter(
            EODReport.report_date == target_date
        ).all()
    }
    return [
        {"id": m.id, "name": m.name, "phone": m.phone}
        for m in all_members
        if m.id not in submitted_ids
    ]


# ── LIST ALL EOD REPORTS ──────────────────────────────────────────────────────
@router.get("/", response_model=List[EODOut])
def list_eod_reports(
    project_id:  Optional[int]  = None,
    user_id:     Optional[int]  = None,
    report_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(EODReport)

    # Team Member — sirf apne reports
    if current_user.role == UserRole.TEAM_MEMBER:
        query = query.filter(
            EODReport.user_id == current_user.id
        )

    # Project Head — sirf apne projects ke reports
    elif current_user.role == UserRole.PROJECT_HEAD:
        project_ids = [
            p.id for p in db.query(Project).filter(
                Project.project_head_id == current_user.id
            ).all()
        ]
        query = query.filter(
            EODReport.project_id.in_(project_ids)
        )

    # Department Head — sirf apne department ke reports
    elif current_user.role == UserRole.DEPARTMENT_HEAD:
        dept_user_ids = [
            u.id for u in db.query(User).filter(
                User.department_id == current_user.department_id,
                User.is_active     == True
            ).all()
        ]
        query = query.filter(
            EODReport.user_id.in_(dept_user_ids)
        )

    # Optional filters
    if project_id:
        query = query.filter(EODReport.project_id == project_id)
    if user_id:
        query = query.filter(EODReport.user_id == user_id)
    if report_date:
        query = query.filter(EODReport.report_date == report_date)

    reports = query.order_by(EODReport.report_date.desc()).all()

    # ✅ Har report mein user aur project details attach karo
    result = []
    for report in reports:

        # User details
        user = db.query(User).filter(User.id == report.user_id).first()

        # Department name
        dept_name = None
        if user and user.department_id:
            from app.models.models import Department
            dept = db.query(Department).filter(
                Department.id == user.department_id
            ).first()
            dept_name = dept.name if dept else None

        # Project details
        project = db.query(Project).filter(
            Project.id == report.project_id
        ).first()

        # Build response object
        report_dict = {
            "id":               report.id,
            "user_id":          report.user_id,
            "project_id":       report.project_id,
            "report_date":      report.report_date,
            "completed_work":   report.completed_work,
            "pending_work":     report.pending_work,
            "delay_reason":     report.delay_reason,
            "tomorrow_plan":    report.tomorrow_plan,
            "support_required": report.support_required,
            "submitted_at":     report.submitted_at,
            "user": {
                "id":         user.id         if user else None,
                "name":       user.name       if user else None,
                "role":       user.role       if user else None,
                "department": dept_name,
            } if user else None,
            "project": {
                "id":   project.id   if project else None,
                "name": project.name if project else None,
            } if project else None,
        }
        result.append(report_dict)

    return result