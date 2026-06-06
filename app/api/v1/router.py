from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, daily_todo, departments, performance, scheduler_test, users, projects, tasks, meetings, eod, dashboard, notifications
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(meetings.router)
api_router.include_router(eod.router)
api_router.include_router(dashboard.router)
api_router.include_router(notifications.router)
api_router.include_router(departments.router)
api_router.include_router(daily_todo.router) 
api_router.include_router(performance.router)
api_router.include_router(scheduler_test.router)
