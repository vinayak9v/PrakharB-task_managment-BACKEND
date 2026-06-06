from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Department
from app.schemas.department import DepartmentOut

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


# ─── Get All Departments ─────────────────────────────────────────────────────

@router.get("/", response_model=list[DepartmentOut])
def get_all_departments(
    db: Session = Depends(get_db)
):

    departments = db.query(Department).all()

    return departments