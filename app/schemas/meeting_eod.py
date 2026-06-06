from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date, time


# ─── Meeting Schemas ──────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: str
    project_id: int
    meeting_date: date
    meeting_time: Optional[time] = None
    participants: Optional[List[int]] = []   # list of user_ids
    meeting_link: Optional[str] = None
    raw_notes: Optional[str] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    raw_notes: Optional[str] = None
    next_followup_date: Optional[date] = None


class MeetingOut(BaseModel):
    id: int
    title: str
    project_id: int
    meeting_date: date
    meeting_time: Optional[time]
    participants: Optional[List[Any]]
    raw_notes: Optional[str]
    ai_summary: Optional[str]
    key_decisions: Optional[List[Any]]
    pending_approvals: Optional[List[Any]]
    next_followup_date: Optional[date]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── EOD Schemas ──────────────────────────────────────────────────────────────

class EODCreate(BaseModel):
    project_id: int
    completed_work: str
    pending_work: Optional[str] = None
    delay_reason: Optional[str] = None
    tomorrow_plan: Optional[str] = None
    support_required: Optional[str] = None


class UserBasicInfo(BaseModel):
    id:         int
    name:       str
    role:       str
    department: Optional[str] = None   # department name

    model_config = {"from_attributes": True}


class ProjectBasicInfo(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}


class EODOut(BaseModel):
    id: int
    user_id: int
    project_id: int
    report_date: date
    completed_work: str
    pending_work: Optional[str]
    delay_reason: Optional[str]
    tomorrow_plan: Optional[str]
    support_required: Optional[str]
    submitted_at: datetime
    user:    Optional[UserBasicInfo]    = None
    project: Optional[ProjectBasicInfo] = None

    model_config = {"from_attributes": True}


class EODDailySummary(BaseModel):
    date: date
    total_members: int
    submitted_count: int
    not_submitted_count: int
    not_submitted_members: List[dict]
    submitted_reports: List[EODOut]
