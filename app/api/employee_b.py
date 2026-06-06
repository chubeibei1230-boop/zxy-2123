from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import require_role

router = APIRouter(prefix="/employee-b", tags=["员工B-复核管理"], dependencies=[Depends(require_role(["admin", "employee_b"]))])


@router.get("/pending-bookings", response_model=List[schemas.BookingResponse])
def get_pending_bookings(
    room_id: Optional[int] = None,
    department_id: Optional[int] = None,
    only_conflict: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if only_conflict:
        status_list = ["conflict"]
    else:
        status_list = ["pending", "conflict"]
    bookings = []
    for status in status_list:
        status_bookings = crud.get_bookings(
            db,
            room_id=room_id,
            department_id=department_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        bookings.extend(status_bookings)
    bookings.sort(key=lambda b: b.start_time, reverse=True)
    return bookings[skip:skip+limit]


@router.get("/bookings/{booking_id}", response_model=schemas.BookingResponse)
def get_booking_detail(booking_id: int, db: Session = Depends(get_db)):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    return booking


@router.post("/bookings/{booking_id}/approve", response_model=schemas.BookingResponse)
def approve_booking(
    booking_id: int,
    review_comment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status == "approved":
        raise HTTPException(status_code=400, detail="该预约已通过")
    if booking.status == "rejected":
        raise HTTPException(status_code=400, detail="该预约已被拒绝")
    updated = crud.update_booking_status(
        db,
        booking_id=booking_id,
        status="approved",
        reviewer_id=current_user.id,
        review_comment=review_comment
    )
    return updated


@router.post("/bookings/{booking_id}/reject", response_model=schemas.BookingResponse)
def reject_booking(
    booking_id: int,
    review_comment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status == "approved":
        raise HTTPException(status_code=400, detail="该预约已通过")
    if booking.status == "rejected":
        raise HTTPException(status_code=400, detail="该预约已被拒绝")
    if not review_comment:
        raise HTTPException(status_code=400, detail="拒绝时必须填写复核意见")
    updated = crud.update_booking_status(
        db,
        booking_id=booking_id,
        status="rejected",
        reviewer_id=current_user.id,
        review_comment=review_comment
    )
    return updated


@router.get("/occupancies", response_model=List[schemas.TemporaryOccupancyResponse])
def list_temporary_occupancies(
    room_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return crud.get_temporary_occupancies(
        db,
        room_id=room_id,
        skip=skip,
        limit=limit
    )


@router.get("/pending-changes", response_model=List[schemas.BookingChangeResponse])
def get_pending_changes(
    room_id: Optional[int] = None,
    department_id: Optional[int] = None,
    only_conflict: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if only_conflict:
        status_list = ["conflict"]
    else:
        status_list = ["pending", "conflict"]
    changes = []
    for status in status_list:
        status_changes = crud.get_booking_changes(
            db,
            status=status,
            skip=skip,
            limit=limit,
        )
        if room_id:
            status_changes = [c for c in status_changes if c.new_room_id == room_id]
        if department_id:
            status_changes = [c for c in status_changes if c.new_department_id == department_id]
        changes.extend(status_changes)
    changes.sort(key=lambda c: c.created_at, reverse=True)
    return changes[skip:skip+limit]


@router.get("/changes/{change_id}", response_model=schemas.BookingChangeResponse)
def get_change_detail(
    change_id: int,
    db: Session = Depends(get_db)
):
    change = crud.get_booking_change(db, change_id=change_id)
    if not change:
        raise HTTPException(status_code=404, detail="变更申请不存在")
    return change


@router.post("/changes/{change_id}/approve", response_model=schemas.BookingChangeResponse)
def approve_change(
    change_id: int,
    review_comment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    change = crud.get_booking_change(db, change_id=change_id)
    if not change:
        raise HTTPException(status_code=404, detail="变更申请不存在")
    if change.status == "approved":
        raise HTTPException(status_code=400, detail="该变更申请已通过")
    if change.status == "rejected":
        raise HTTPException(status_code=400, detail="该变更申请已被拒绝")
    updated = crud.review_booking_change(
        db,
        change_id=change_id,
        status="approved",
        reviewer_id=current_user.id,
        review_comment=review_comment
    )
    if not updated:
        raise HTTPException(status_code=500, detail="审核失败")
    return updated


@router.post("/changes/{change_id}/reject", response_model=schemas.BookingChangeResponse)
def reject_change(
    change_id: int,
    review_comment: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    change = crud.get_booking_change(db, change_id=change_id)
    if not change:
        raise HTTPException(status_code=404, detail="变更申请不存在")
    if change.status == "approved":
        raise HTTPException(status_code=400, detail="该变更申请已通过")
    if change.status == "rejected":
        raise HTTPException(status_code=400, detail="该变更申请已被拒绝")
    if not review_comment:
        raise HTTPException(status_code=400, detail="拒绝时必须填写复核意见")
    updated = crud.review_booking_change(
        db,
        change_id=change_id,
        status="rejected",
        reviewer_id=current_user.id,
        review_comment=review_comment
    )
    if not updated:
        raise HTTPException(status_code=500, detail="审核失败")
    return updated
