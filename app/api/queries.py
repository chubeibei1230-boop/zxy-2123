from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/query", tags=["查询统计"])


@router.get("/bookings", response_model=List[schemas.BookingResponse])
def query_bookings(
    room_id: Optional[int] = Query(None, description="会议室ID"),
    department_id: Optional[int] = Query(None, description="部门ID"),
    applicant_id: Optional[int] = Query(None, description="申请人ID"),
    status: Optional[str] = Query(None, description="状态: pending/conflict/approved/rejected"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误，应为YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
    if status and status not in ["pending", "conflict", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    return crud.get_bookings(
        db,
        room_id=room_id,
        department_id=department_id,
        applicant_id=applicant_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        skip=skip,
        limit=limit
    )


@router.get("/rooms", response_model=List[schemas.MeetingRoomResponse])
def list_rooms(
    only_active: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_meeting_rooms(db, skip=skip, limit=limit, only_active=only_active)


@router.get("/departments", response_model=List[schemas.DepartmentResponse])
def list_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_departments(db, skip=skip, limit=limit)


@router.get("/equipments", response_model=List[schemas.EquipmentResponse])
def list_equipments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_equipments(db, skip=skip, limit=limit)


@router.get("/occupancy-stats", response_model=List[schemas.OccupancyStatsResponse])
def get_occupancy_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误，应为YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
    stats = crud.get_occupancy_stats(db, start_date=start_dt, end_date=end_dt)
    return stats


@router.get("/import-errors/{batch_id}", response_model=List[schemas.ImportErrorResponse])
def get_import_errors(
    batch_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    batch = crud.get_import_batch(db, batch_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return crud.get_import_errors(db, batch_id=batch_id, skip=skip, limit=limit)


@router.get("/pending-review-count")
def get_pending_review_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    pending = crud.get_bookings(db, status="pending", limit=10000)
    conflict = crud.get_bookings(db, status="conflict", limit=10000)
    return {
        "pending_count": len(pending),
        "conflict_count": len(conflict),
        "total_to_review": len(pending) + len(conflict)
    }
