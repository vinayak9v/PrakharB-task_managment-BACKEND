from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from app.db.session import get_db
from app.models.models import (
    Task, User, Project, TaskFollowUp, AuditLog,
    TaskStatus, TaskPriority, EscalationLevel, UserRole
)
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskStatusUpdate,
    TaskOut, TaskOutDetail, TaskFollowUpCreate, TaskFollowUpOut
)
from app.core.dependencies import (
    get_current_user, require_admin_or_above, require_project_head_or_above
)
from app.services.whatsapp_service import (
    send_whatsapp_message,
    task_assigned_message,
    task_delay_alert_message,
    escalation_to_admin_message
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskOut)
async def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    # Verify project and assignee exist
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignee = db.query(User).filter(User.id == body.assigned_to_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    task = Task(
        title=body.title,
        description=body.description,
        project_id=body.project_id,
        assigned_to_id=body.assigned_to_id,
        assigned_by_id=current_user.id,
        priority=body.priority,
        due_date=body.due_date,
        due_time=body.due_time,
        remarks=body.remarks,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Send WhatsApp notification to assignee
    deadline_str = str(body.due_date)
    if body.due_time:
        deadline_str += f" at {body.due_time}"

    msg = task_assigned_message(
        name=assignee.name,
        project=project.name,
        task=task.title,
        deadline=deadline_str,
        priority=task.priority.value.upper()
    )
    await send_whatsapp_message(assignee.phone, msg)

    # Audit
    db.add(AuditLog(user_id=current_user.id, action="task_created", module="task",
                    detail={"task_id": task.id, "assigned_to": assignee.name}))
    db.commit()

    return task

@router.get("/", response_model=List[TaskOut])
def list_tasks(
    project_id:   Optional[int]          = None,
    status:       Optional[TaskStatus]   = None,
    priority:     Optional[TaskPriority] = None,
    assigned_to_id: Optional[int]        = None,
    overdue_only: bool                   = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task).filter(Task.is_deleted == False)

    # ── Role based filtering ──────────────────────────────────────────────────

    # Team Member — sirf apne tasks
    if current_user.role == UserRole.TEAM_MEMBER:
        query = query.filter(Task.assigned_to_id == current_user.id)

    # Project Head — sirf apne projects ke tasks
    elif current_user.role == UserRole.PROJECT_HEAD:
        my_project_ids = [
            p.id for p in db.query(Project).filter(
                Project.project_head_id == current_user.id
            ).all()
        ]
        query = query.filter(Task.project_id.in_(my_project_ids))

    # Department Head — sirf apne department ke users ke tasks
    elif current_user.role == UserRole.DEPARTMENT_HEAD:
        dept_user_ids = [
            u.id for u in db.query(User).filter(
                User.department_id == current_user.department_id
            ).all()
        ]
        query = query.filter(Task.assigned_to_id.in_(dept_user_ids))

    # Admin / Super Admin — sab tasks
    # No filter needed

    # ── Optional filters ──────────────────────────────────────────────────────
    if project_id:
        query = query.filter(Task.project_id == project_id)

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if assigned_to_id and current_user.role != UserRole.TEAM_MEMBER:
        query = query.filter(Task.assigned_to_id == assigned_to_id)

    if overdue_only:
        query = query.filter(
            Task.due_date < date.today(),
            Task.status.notin_([TaskStatus.COMPLETED])
        )

    return query.order_by(Task.due_date.asc()).all()




@router.get("/overdue", response_model=List[TaskOut])
def get_overdue_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_above)
):
    return db.query(Task).filter(
        Task.due_date < date.today(),
        Task.status.notin_([TaskStatus.COMPLETED]),
        Task.is_deleted == False
    ).order_by(Task.due_date.asc()).all()


@router.get("/{task_id}", response_model=TaskOutDetail)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task





@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # ✅ Sirf yeh 6 lines nai hain — upar neeche sab same hai
    if body.assigned_to_id:
        new_assignee = db.query(User).filter(
            User.id        == body.assigned_to_id,
            User.is_active == True
        ).first()
        if not new_assignee:
            raise HTTPException(
                status_code=404,
                detail="New assignee not found or inactive"
            )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskOut)
async def update_task_status(
    task_id: int,
    body: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Team member can only update their own tasks
    if current_user.role == UserRole.TEAM_MEMBER and task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot update others' tasks")

    old_status = task.status
    task.status = body.status
    task.updated_at = datetime.utcnow()

    if body.delay_reason:
        task.delay_reason = body.delay_reason
    if body.remarks:
        task.remarks = body.remarks
    if body.status == TaskStatus.COMPLETED:
        task.completed_at = datetime.utcnow()

    # Escalation if delayed
    if body.status == TaskStatus.DELAYED:
        await _handle_escalation(task, db)

    db.add(AuditLog(user_id=current_user.id, action="status_updated", module="task",
                    detail={"task_id": task.id, "old": old_status, "new": body.status}))
    db.commit()
    db.refresh(task)
    return task


async def _handle_escalation(task: Task, db: Session):
    """Escalate delayed task — Level 1 → Level 2 → Level 3."""
    project = db.query(Project).filter(Project.id == task.project_id).first()
    assignee = db.query(User).filter(User.id == task.assigned_to_id).first()

    current_level = task.escalation_level

    if current_level is None:
        task.escalation_level = EscalationLevel.LEVEL_1
        msg = task_delay_alert_message(
            name=assignee.name,
            task=task.title,
            project=project.name if project else "N/A",
            original_deadline=str(task.due_date)
        )
        await send_whatsapp_message(assignee.phone, msg)

    elif current_level == EscalationLevel.LEVEL_1 and project and project.project_head_id:
        task.escalation_level = EscalationLevel.LEVEL_2
        head = db.query(User).filter(User.id == project.project_head_id).first()
        if head:
            msg = (f"⚠️ Task Escalation Alert\n\nProject: {project.name}\n"
                   f"Task: {task.title}\nAssigned To: {assignee.name}\n"
                   f"Deadline: {task.due_date}\nStatus: DELAYED")
            await send_whatsapp_message(head.phone, msg)

    elif current_level == EscalationLevel.LEVEL_2:
        task.escalation_level = EscalationLevel.LEVEL_3
        # Notify Prakhar Sir (Super Admin)
        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        if admin:
            msg = escalation_to_admin_message(
                task=task.title,
                project=project.name if project else "N/A",
                assigned_to=assignee.name,
                deadline=str(task.due_date),
                delay_reason=task.delay_reason or "Not provided"
            )
            await send_whatsapp_message(admin.phone, msg)


@router.post("/{task_id}/followup", response_model=TaskFollowUpOut)
def add_followup(
    task_id: int,
    body: TaskFollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    followup = TaskFollowUp(
        task_id=task_id,
        note=body.note,
        updated_by=current_user.id
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_head_or_above)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_deleted = True
    db.commit()
    return {"message": "Task deleted"}
