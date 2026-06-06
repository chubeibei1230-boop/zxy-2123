from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.recommendation import generate_recommendations

router = APIRouter(prefix="/query", tags=["查询统计"])


@router.get("/bookings", response_model=List[schemas.BookingResponse])
def query_bookings(
    room_id: Optional[int] = Query(None, description="会议室ID"),
    department_id: Optional[int] = Query(None, description="部门ID"),
    applicant_id: Optional[int] = Query(None, description="申请人ID"),
    status: Optional[str] = Query(None, description="状态: pending/conflict/approved/rejected"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    is_cancelled: Optional[bool] = Query(None, description="是否已取消"),
    is_modified: Optional[bool] = Query(None, description="是否已变更"),
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
        is_cancelled=is_cancelled,
        is_modified=is_modified,
        skip=skip,
        limit=limit
    )


@router.get("/changes", response_model=List[schemas.BookingChangeResponse])
def query_changes(
    booking_id: Optional[int] = Query(None, description="预约ID"),
    status: Optional[str] = Query(None, description="状态: pending/conflict/approved/rejected"),
    applicant_id: Optional[int] = Query(None, description="申请人ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if status and status not in ["pending", "conflict", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    return crud.get_booking_changes(
        db,
        booking_id=booking_id,
        status=status,
        applicant_id=applicant_id,
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


@router.get("/conflict-bookings", response_model=schemas.ConflictBookingStatsResponse)
def get_conflict_bookings_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    include_resolved: bool = Query(True, description="是否包含已处理的冲突"),
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
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
    
    if not start_dt:
        start_dt = datetime.utcnow() - timedelta(days=30)
    if not end_dt:
        end_dt = datetime.utcnow() + timedelta(days=30)
    
    records = []
    
    conflict_bookings = crud.get_bookings(
        db,
        start_date=start_dt,
        end_date=end_dt,
        limit=10000
    )
    
    for booking in conflict_bookings:
        has_conflict = booking.status == "conflict" or booking.conflict_info
        if not has_conflict and not include_resolved:
            continue
        
        if booking.status in ["approved", "rejected"] and not booking.conflict_info:
            if not include_resolved:
                continue
        
        resolution_status = "pending"
        resolved_at = None
        recommended_solution = None
        
        if booking.status == "conflict":
            resolution_status = "pending"
        elif booking.status == "approved":
            if booking.conflict_info:
                resolution_status = "resolved_with_conflict"
            else:
                resolution_status = "resolved_normal"
            resolved_at = booking.review_time
        elif booking.status == "rejected":
            resolution_status = "resolved_rejected"
            resolved_at = booking.review_time
        
        if has_conflict:
            try:
                recs = generate_recommendations(
                    db=db,
                    original_room_id=booking.room_id,
                    original_start=booking.start_time,
                    original_end=booking.end_time,
                    attendee_count=booking.attendee_count,
                    department_id=booking.department_id,
                    required_equipments=[
                        schemas.BookingEquipmentCreate(
                            equipment_id=eq.equipment_id,
                            quantity=eq.quantity
                        ) for eq in booking.equipments
                    ],
                    exclude_booking_id=booking.id,
                    max_recommendations=3,
                    title_keywords=booking.title
                )
                if recs.recommendations:
                    top = recs.recommendations[0]
                    recommended_solution = f"推荐: {top.room.name} {top.start_time.strftime('%m-%d %H:%M')}-{top.end_time.strftime('%H:%M')}"
            except Exception:
                pass
        
        record = schemas.ConflictBookingRecord(
            id=booking.id,
            type="预约",
            title=booking.title,
            original_room=booking.room.name if booking.room else "未知",
            original_start_time=booking.start_time,
            original_end_time=booking.end_time,
            attendee_count=booking.attendee_count,
            department=booking.department.name if booking.department else "未知",
            applicant=booking.applicant.full_name if booking.applicant else "未知",
            status=booking.status,
            conflict_info=booking.conflict_info,
            recommended_solution=recommended_solution,
            resolution_status=resolution_status,
            resolved_at=resolved_at,
            created_at=booking.created_at
        )
        records.append(record)
    
    conflict_changes = crud.get_booking_changes(
        db,
        limit=10000
    )
    
    for change in conflict_changes:
        has_conflict = change.status == "conflict" or change.conflict_info
        if not has_conflict and not include_resolved:
            continue
        
        if change.status in ["approved", "rejected"] and not change.conflict_info:
            if not include_resolved:
                continue
        
        if start_dt and change.created_at < start_dt:
            continue
        if end_dt and change.created_at > end_dt:
            continue
        
        resolution_status = "pending"
        resolved_at = None
        recommended_solution = None
        
        if change.status == "conflict":
            resolution_status = "pending"
        elif change.status == "approved":
            if change.conflict_info:
                resolution_status = "resolved_with_conflict"
            else:
                resolution_status = "resolved_normal"
            resolved_at = change.review_time
        elif change.status == "rejected":
            resolution_status = "resolved_rejected"
            resolved_at = change.review_time
        
        room_id = change.new_room_id if change.new_room_id else change.old_room_id
        start_time = change.new_start_time if change.new_start_time else change.old_start_time
        end_time = change.new_end_time if change.new_end_time else change.old_end_time
        attendee_count = change.new_attendee_count if change.new_attendee_count else change.old_attendee_count
        room_name = change.new_room.name if (change.new_room) else (change.old_room.name if change.old_room else "未知")
        
        if has_conflict:
            try:
                recs = generate_recommendations(
                    db=db,
                    original_room_id=room_id,
                    original_start=start_time,
                    original_end=end_time,
                    attendee_count=attendee_count,
                    department_id=change.new_department_id if change.new_department_id else change.old_department_id,
                    required_equipments=[],
                    exclude_booking_id=change.booking_id,
                    max_recommendations=3,
                    title_keywords=change.new_title if change.new_title else change.old_title
                )
                if recs.recommendations:
                    top = recs.recommendations[0]
                    recommended_solution = f"推荐: {top.room.name} {top.start_time.strftime('%m-%d %H:%M')}-{top.end_time.strftime('%H:%M')}"
            except Exception:
                pass
        
        record = schemas.ConflictBookingRecord(
            id=change.id,
            type="变更",
            title=change.new_title if change.new_title else (change.old_title or "变更申请"),
            original_room=room_name,
            original_start_time=start_time,
            original_end_time=end_time,
            attendee_count=attendee_count,
            department=change.new_department.name if change.new_department else (change.old_department.name if change.old_department else "未知"),
            applicant=change.applicant.full_name if change.applicant else "未知",
            status=change.status,
            conflict_info=change.conflict_info,
            recommended_solution=recommended_solution,
            resolution_status=resolution_status,
            resolved_at=resolved_at,
            created_at=change.created_at
        )
        records.append(record)
    
    records.sort(key=lambda x: x.created_at, reverse=True)
    
    total_conflicts = len(records)
    resolved_count = sum(1 for r in records if r.resolution_status.startswith("resolved"))
    pending_count = total_conflicts - resolved_count
    resolved_with_conflict = sum(1 for r in records if r.resolution_status == "resolved_with_conflict")
    resolved_by_rejection = sum(1 for r in records if r.resolution_status == "resolved_rejected")
    
    return schemas.ConflictBookingStatsResponse(
        start_date=start_dt,
        end_date=end_dt,
        total_conflicts=total_conflicts,
        resolved_count=resolved_count,
        pending_count=pending_count,
        resolved_with_conflict=resolved_with_conflict,
        resolved_by_rejection=resolved_by_rejection,
        records=records
    )
