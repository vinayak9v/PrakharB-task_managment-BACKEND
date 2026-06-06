"""
All ORM models for AI-PS Platform.
Tables are auto-created on startup via Base.metadata.create_all()
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum, Date, Time, JSON
)
from sqlalchemy.orm import relationship
from app.db.session import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PROJECT_HEAD = "project_head"
    DEPARTMENT_HEAD = "department_head"
    TEAM_MEMBER = "team_member"


class TaskPriority(str, PyEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, PyEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    DELAYED = "delayed"


class ProjectStatus(str, PyEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class NotificationChannel(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SYSTEM = "system"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EscalationLevel(str, PyEnum):
    LEVEL_1 = "level_1"   # Assigned person
    LEVEL_2 = "level_2"   # Project head
    LEVEL_3 = "level_3"   # Prakhar Sir
    RESOLVED = "resolved"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TEAM_MEMBER, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assignee")
    created_tasks = relationship("Task", foreign_keys="Task.assigned_by_id", back_populates="creator")
    eod_reports = relationship("EODReport", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    project_memberships = relationship("ProjectMember", back_populates="user")
    department = relationship("Department", back_populates="users")

# ─── Projects ─────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    project_head_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project_head = relationship("User", foreign_keys=[project_head_id])
    tasks = relationship("Task", back_populates="project")
    meetings = relationship("Meeting", back_populates="project")
    eod_reports = relationship("EODReport", back_populates="project")
    members = relationship("ProjectMember", back_populates="project")


class ProjectMember(Base):
    """Many-to-many: User <-> Project"""
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")


# ─── Tasks ────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    due_date = Column(Date, nullable=False)
    due_time = Column(Time, nullable=True)
    delay_reason = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    attachment_url = Column(String(500), nullable=True)
    escalation_level = Column(Enum(EscalationLevel), nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[assigned_by_id], back_populates="created_tasks")
    follow_ups = relationship("TaskFollowUp", back_populates="task")
    meeting = relationship("Meeting", back_populates="action_items")


class TaskFollowUp(Base):
    __tablename__ = "task_follow_ups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    note = Column(Text, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="follow_ups")
    user = relationship("User")


# ─── Meetings ─────────────────────────────────────────────────────────────────

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    meeting_date = Column(Date, nullable=False)
    meeting_time = Column(Time, nullable=True)
    meeting_link = Column(String(500), nullable=True)
    participants = Column(JSON, nullable=True)          # list of user_ids
    raw_notes = Column(Text, nullable=True)             # manual notes
    transcript = Column(Text, nullable=True)            # audio → text
    ai_summary = Column(Text, nullable=True)            # AI generated
    key_decisions = Column(JSON, nullable=True)         # list of strings
    pending_approvals = Column(JSON, nullable=True)     # list of strings
    next_followup_date = Column(Date, nullable=True)
    audio_file_url = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="meetings")
    creator = relationship("User")
    action_items = relationship("Task", back_populates="meeting")


# ─── EOD Reports ──────────────────────────────────────────────────────────────

class EODReport(Base):
    __tablename__ = "eod_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    completed_work = Column(Text, nullable=False)
    pending_work = Column(Text, nullable=True)
    delay_reason = Column(Text, nullable=True)
    tomorrow_plan = Column(Text, nullable=True)
    support_required = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="eod_reports")
    project = relationship("Project", back_populates="eod_reports")


# ─── Notifications ────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)  # task_assigned, reminder, eod_reminder, etc.
    message = Column(Text, nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.WHATSAPP)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    reference_id = Column(Integer, nullable=True)    # task_id or meeting_id
    reference_type = Column(String(50), nullable=True)  # "task", "meeting", "eod"
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


# ─── Audit Logs ───────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)   # "task_created", "status_updated", etc.
    module = Column(String(50), nullable=False)    # "task", "user", "eod", "meeting"
    detail = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True)

    users = relationship("User", back_populates="department")