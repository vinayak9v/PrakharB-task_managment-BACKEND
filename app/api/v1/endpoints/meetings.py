from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.models.models import Meeting, Task, User, Project, TaskStatus, TaskPriority
from app.schemas.meeting_eod import MeetingCreate, MeetingUpdate, MeetingOut
from app.core.dependencies import get_current_user, require_project_head_or_above
from app.services.ai_service import generate_meeting_summary, extract_tasks_from_text

from app.services.whatsapp_service import (
    send_whatsapp_message,
    meeting_invite_message    # ← Yeh add karo
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post("/", response_model=MeetingOut)
async def create_meeting(
    body: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    meeting = Meeting(
        title          = body.title,
        project_id     = body.project_id,
        meeting_date   = body.meeting_date,
        meeting_time   = body.meeting_time,
        participants   = body.participants,
        raw_notes      = body.raw_notes,
        meeting_link   = body.meeting_link,   # ← Yeh add karo
        created_by     = current_user.id,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # WhatsApp — saare participants ko bhejo
    if body.participants:
        time_str     = str(body.meeting_time) if body.meeting_time else "Time not set"
        project      = db.query(Project).filter(Project.id == body.project_id).first()
        project_name = project.name if project else "N/A"

        for user_id in body.participants:
            user = db.query(User).filter(
                User.id        == user_id,
                User.is_active == True
            ).first()

            if user and user.phone:
                msg = meeting_invite_message(
                    name          = user.name,
                    meeting_title = body.title,
                    project       = project_name,
                    meeting_date  = str(body.meeting_date),
                    meeting_time  = time_str,
                    organized_by  = current_user.name,
                    meeting_link  = body.meeting_link or "Link not provided"  # ← Yeh add karo
                )
                await send_whatsapp_message(user.phone, msg)

    return meeting  


@router.get("/", response_model=List[MeetingOut])
def list_meetings(
    project_id: Optional[int] = None,
    meeting_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Meeting)
    if project_id:
        query = query.filter(Meeting.project_id == project_id)
    if meeting_date:
        query = query.filter(Meeting.meeting_date == meeting_date)
    return query.order_by(Meeting.meeting_date.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.post("/{meeting_id}/generate-summary", response_model=MeetingOut)
async def generate_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    """AI generates meeting summary from notes or transcript."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    content = meeting.transcript or meeting.raw_notes
    if not content:
        raise HTTPException(status_code=400, detail="No notes or transcript to summarize")

    result = await generate_meeting_summary(content)

    meeting.ai_summary = result.get("summary", "")
    meeting.key_decisions = result.get("decisions", [])
    meeting.pending_approvals = result.get("pending_approvals", [])

    db.commit()
    db.refresh(meeting)

    # Auto-create tasks from action items
    action_items = result.get("action_items", [])
    project = db.query(Project).filter(Project.id == meeting.project_id).first()

    for item in action_items:
        task = Task(
            title=item.get("title", "Untitled Task"),
            description=item.get("description", ""),
            project_id=meeting.project_id,
            assigned_by_id=current_user.id,
            assigned_to_id=current_user.id,   # default to creator; admin should reassign
            priority=TaskPriority.MEDIUM,
            due_date=date.today(),              # needs to be updated manually
            status=TaskStatus.NOT_STARTED,
            meeting_id=meeting_id,
            remarks=f"Auto-created from meeting: {meeting.title}. Owner: {item.get('owner', 'TBD')}"
        )
        db.add(task)

    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/upload-notes")
async def upload_notes(
    meeting_id: int,
    notes: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    """Upload raw meeting notes — AI will process on generate-summary call."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.raw_notes = notes
    db.commit()
    return {"message": "Notes uploaded. Call /generate-summary to process with AI."}


@router.put("/{meeting_id}", response_model=MeetingOut)
def update_meeting(
    meeting_id: int,
    body: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(meeting, field, value)
    db.commit()
    db.refresh(meeting)
    return meeting
