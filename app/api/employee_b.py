from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import require_role
from app.core.recommendation import generate_recommendations

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


class BookingDetailWithRecommendation(schemas.BookingResponse):
    recommendations: Optional[schemas.RecommendationResponse] = None
    reassignments: List[schemas.ReassignmentResponse] = []


@router.get("/bookings/{booking_id}", response_model=BookingDetailWithRecommendation)
def get_booking_detail(booking_id: int, db: Session = Depends(get_db)):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    
    reassignments = crud.get_reassignments(db, booking_id=booking_id)
    reassignment_responses = []
    for r in reassignments:
        reassignment_responses.append(
            schemas.ReassignmentResponse(
                id=r.id,
                booking_id=r.booking_id,
                change_id=r.change_id,
                occupancy_id=r.occupancy_id,
                source_type=r.source_type,
                original_room_id=r.original_room_id,
                original_room=schemas.MeetingRoomResponse(
                    id=r.original_room.id,
                    name=r.original_room.name,
                    capacity=r.original_room.capacity,
                    location=r.original_room.location,
                    description=r.original_room.description,
                    is_active=r.original_room.is_active,
                    equipments=[
                        schemas.RoomEquipmentResponse(
                            id=re.id,
                            equipment_id=re.equipment_id,
                            quantity=re.quantity,
                            equipment=schemas.EquipmentResponse(
                                id=re.equipment.id,
                                name=re.equipment.name,
                                description=re.equipment.description
                            )
                        ) for re in r.original_room.equipments
                    ]
                ) if r.original_room else None,
                original_start_time=r.original_start_time,
                original_end_time=r.original_end_time,
                original_attendee_count=r.original_attendee_count,
                reassigned_room_id=r.reassigned_room_id,
                reassigned_room=schemas.MeetingRoomResponse(
                    id=r.reassigned_room.id,
                    name=r.reassigned_room.name,
                    capacity=r.reassigned_room.capacity,
                    location=r.reassigned_room.location,
                    description=r.reassigned_room.description,
                    is_active=r.reassigned_room.is_active,
                    equipments=[
                        schemas.RoomEquipmentResponse(
                            id=re.id,
                            equipment_id=re.equipment_id,
                            quantity=re.quantity,
                            equipment=schemas.EquipmentResponse(
                                id=re.equipment.id,
                                name=re.equipment.name,
                                description=re.equipment.description
                            )
                        ) for re in r.reassigned_room.equipments
                    ]
                ) if r.reassigned_room else None,
                reassigned_start_time=r.reassigned_start_time,
                reassigned_end_time=r.reassigned_end_time,
                reassigned_attendee_count=r.reassigned_attendee_count,
                conflict_reasons=r.conflict_reasons,
                recommendation_index=r.recommendation_index,
                match_score=r.match_score,
                recommendation_reasons=r.recommendation_reasons,
                operator_id=r.operator_id,
                operator=schemas.UserResponse(
                    id=r.operator.id,
                    username=r.operator.username,
                    full_name=r.operator.full_name,
                    role=r.operator.role,
                    department_id=r.operator.department_id,
                    is_active=r.operator.is_active
                ) if r.operator else None,
                operated_at=r.operated_at,
                processing_note=r.processing_note,
                status=r.status,
                reviewer_id=r.reviewer_id,
                reviewer=schemas.UserResponse(
                    id=r.reviewer.id,
                    username=r.reviewer.username,
                    full_name=r.reviewer.full_name,
                    role=r.reviewer.role,
                    department_id=r.reviewer.department_id,
                    is_active=r.reviewer.is_active
                ) if r.reviewer else None,
                review_time=r.review_time,
                review_comment=r.review_comment,
                equipment_diffs=[
                    schemas.ReassignmentEquipmentDiffResponse(
                        id=diff.id,
                        equipment_id=diff.equipment_id,
                        old_quantity=diff.old_quantity,
                        new_quantity=diff.new_quantity,
                        diff_type=diff.diff_type,
                        equipment=schemas.EquipmentResponse(
                            id=diff.equipment.id,
                            name=diff.equipment.name,
                            description=diff.equipment.description
                        )
                    ) for diff in r.equipment_diffs
                ]
            )
        )
    
    result = BookingDetailWithRecommendation(
        id=booking.id,
        room_id=booking.room_id,
        title=booking.title,
        start_time=booking.start_time,
        end_time=booking.end_time,
        attendee_count=booking.attendee_count,
        department_id=booking.department_id,
        equipments=[
            schemas.BookingEquipmentResponse(
                id=eq.id,
                equipment_id=eq.equipment_id,
                quantity=eq.quantity,
                equipment=schemas.EquipmentResponse(
                    id=eq.equipment.id,
                    name=eq.equipment.name,
                    description=eq.equipment.description
                ) if eq.equipment else None
            ) for eq in booking.equipments
        ],
        status=booking.status,
        conflict_info=booking.conflict_info,
        applicant_id=booking.applicant_id,
        reviewer_id=booking.reviewer_id,
        review_time=booking.review_time,
        review_comment=booking.review_comment,
        created_at=booking.created_at,
        batch_id=booking.batch_id,
        is_cancelled=booking.is_cancelled,
        cancelled_by_id=booking.cancelled_by_id,
        cancelled_by=schemas.UserResponse(
            id=booking.cancelled_by.id,
            username=booking.cancelled_by.username,
            full_name=booking.cancelled_by.full_name,
            role=booking.cancelled_by.role,
            department_id=booking.cancelled_by.department_id,
            is_active=booking.cancelled_by.is_active
        ) if booking.cancelled_by else None,
        cancelled_at=booking.cancelled_at,
        cancel_reason=booking.cancel_reason,
        is_modified=booking.is_modified,
        last_modified_at=booking.last_modified_at,
        applicant=schemas.UserResponse(
            id=booking.applicant.id,
            username=booking.applicant.username,
            full_name=booking.applicant.full_name,
            role=booking.applicant.role,
            department_id=booking.applicant.department_id,
            is_active=booking.applicant.is_active
        ) if booking.applicant else None,
        department=schemas.DepartmentResponse(
            id=booking.department.id,
            name=booking.department.name,
            description=booking.department.description
        ) if booking.department else None,
        room=schemas.MeetingRoomResponse(
            id=booking.room.id,
            name=booking.room.name,
            capacity=booking.room.capacity,
            location=booking.room.location,
            description=booking.room.description,
            is_active=booking.room.is_active,
            equipments=[
                schemas.RoomEquipmentResponse(
                    id=re.id,
                    equipment_id=re.equipment_id,
                    quantity=re.quantity,
                    equipment=schemas.EquipmentResponse(
                        id=re.equipment.id,
                        name=re.equipment.name,
                        description=re.equipment.description
                    )
                ) for re in booking.room.equipments
            ]
        ) if booking.room else None,
        changes=[
            schemas.BookingChangeResponse(
                id=c.id,
                booking_id=c.booking_id,
                applicant_id=c.applicant_id,
                old_room_id=c.old_room_id,
                new_room_id=c.new_room_id,
                old_title=c.old_title,
                new_title=c.new_title,
                old_start_time=c.old_start_time,
                new_start_time=c.new_start_time,
                old_end_time=c.old_end_time,
                new_end_time=c.new_end_time,
                old_attendee_count=c.old_attendee_count,
                new_attendee_count=c.new_attendee_count,
                old_department_id=c.old_department_id,
                new_department_id=c.new_department_id,
                change_reason=c.change_reason,
                status=c.status,
                conflict_info=c.conflict_info,
                reviewer_id=c.reviewer_id,
                review_time=c.review_time,
                review_comment=c.review_comment,
                created_at=c.created_at
            ) for c in booking.changes
        ],
        reassignments=reassignment_responses
    )
    
    if booking.status == "conflict" or booking.conflict_info:
        recommendations = generate_recommendations(
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
            max_recommendations=5,
            title_keywords=booking.title
        )
        result.recommendations = recommendations
    
    return result


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


class BookingChangeDetailWithRecommendation(schemas.BookingChangeResponse):
    recommendations: Optional[schemas.RecommendationResponse] = None


@router.get("/changes/{change_id}", response_model=BookingChangeDetailWithRecommendation)
def get_change_detail(
    change_id: int,
    db: Session = Depends(get_db)
):
    change = crud.get_booking_change(db, change_id=change_id)
    if not change:
        raise HTTPException(status_code=404, detail="变更申请不存在")
    
    result = BookingChangeDetailWithRecommendation(
        id=change.id,
        booking_id=change.booking_id,
        applicant_id=change.applicant_id,
        applicant=schemas.UserResponse(
            id=change.applicant.id,
            username=change.applicant.username,
            full_name=change.applicant.full_name,
            role=change.applicant.role,
            department_id=change.applicant.department_id,
            is_active=change.applicant.is_active
        ) if change.applicant else None,
        old_room_id=change.old_room_id,
        new_room_id=change.new_room_id,
        old_room=schemas.MeetingRoomResponse(
            id=change.old_room.id,
            name=change.old_room.name,
            capacity=change.old_room.capacity,
            location=change.old_room.location,
            description=change.old_room.description,
            is_active=change.old_room.is_active,
            equipments=[]
        ) if change.old_room else None,
        new_room=schemas.MeetingRoomResponse(
            id=change.new_room.id,
            name=change.new_room.name,
            capacity=change.new_room.capacity,
            location=change.new_room.location,
            description=change.new_room.description,
            is_active=change.new_room.is_active,
            equipments=[]
        ) if change.new_room else None,
        old_title=change.old_title,
        new_title=change.new_title,
        old_start_time=change.old_start_time,
        new_start_time=change.new_start_time,
        old_end_time=change.old_end_time,
        new_end_time=change.new_end_time,
        old_attendee_count=change.old_attendee_count,
        new_attendee_count=change.new_attendee_count,
        old_department_id=change.old_department_id,
        new_department_id=change.new_department_id,
        old_department=schemas.DepartmentResponse(
            id=change.old_department.id,
            name=change.old_department.name,
            description=change.old_department.description
        ) if change.old_department else None,
        new_department=schemas.DepartmentResponse(
            id=change.new_department.id,
            name=change.new_department.name,
            description=change.new_department.description
        ) if change.new_department else None,
        change_reason=change.change_reason,
        status=change.status,
        conflict_info=change.conflict_info,
        reviewer_id=change.reviewer_id,
        reviewer=schemas.UserResponse(
            id=change.reviewer.id,
            username=change.reviewer.username,
            full_name=change.reviewer.full_name,
            role=change.reviewer.role,
            department_id=change.reviewer.department_id,
            is_active=change.reviewer.is_active
        ) if change.reviewer else None,
        review_time=change.review_time,
        review_comment=change.review_comment,
        created_at=change.created_at,
        equipment_changes=[
            schemas.BookingEquipmentChangeResponse(
                id=ec.id,
                equipment_id=ec.equipment_id,
                equipment=schemas.EquipmentResponse(
                    id=ec.equipment.id,
                    name=ec.equipment.name,
                    description=ec.equipment.description
                ) if ec.equipment else None,
                old_quantity=ec.old_quantity,
                new_quantity=ec.new_quantity,
                change_type=ec.change_type
            ) for ec in change.equipment_changes
        ]
    )
    
    if change.status == "conflict" or change.conflict_info:
        room_id = change.new_room_id if change.new_room_id else change.old_room_id
        start_time = change.new_start_time if change.new_start_time else change.old_start_time
        end_time = change.new_end_time if change.new_end_time else change.old_end_time
        attendee_count = change.new_attendee_count if change.new_attendee_count else change.old_attendee_count
        department_id = change.new_department_id if change.new_department_id else change.old_department_id
        
        equipment_reqs = []
        if change.equipment_changes:
            old_equip_map = {}
            if change.booking and change.booking.equipments:
                old_equip_map = {eq.equipment_id: eq.quantity for eq in change.booking.equipments}
            for ec in change.equipment_changes:
                if ec.change_type == "add" or ec.change_type == "modify":
                    equipment_reqs.append(schemas.BookingEquipmentCreate(
                        equipment_id=ec.equipment_id,
                        quantity=ec.new_quantity or 1
                    ))
                elif ec.change_type == "remove":
                    pass
            if not equipment_reqs and change.booking and change.booking.equipments:
                has_remove = any(ec.change_type == "remove" for ec in change.equipment_changes)
                if not has_remove:
                    equipment_reqs = [
                        schemas.BookingEquipmentCreate(
                            equipment_id=eq.equipment_id,
                            quantity=eq.quantity
                        ) for eq in change.booking.equipments
                    ]
        
        recommendations = generate_recommendations(
            db=db,
            original_room_id=room_id,
            original_start=start_time,
            original_end=end_time,
            attendee_count=attendee_count,
            department_id=department_id,
            required_equipments=equipment_reqs,
            exclude_booking_id=change.booking_id,
            max_recommendations=5,
            title_keywords=change.new_title if change.new_title else change.old_title
        )
        result.recommendations = recommendations
    
    return result


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


@router.get("/pending-reassignments", response_model=List[schemas.ReassignmentResponse])
def get_pending_reassignments(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    if status:
        status_list = [status]
    else:
        status_list = ["pending", "conflict"]
    reassignments = []
    for s in status_list:
        status_reassignments = crud.get_reassignments(
            db,
            status=s,
            skip=skip,
            limit=limit
        )
        reassignments.extend(status_reassignments)
    reassignments.sort(key=lambda r: r.operated_at, reverse=True)
    return reassignments[skip:skip+limit]


@router.get("/reassignments/{reassignment_id}", response_model=schemas.ReassignmentWithDetailsResponse)
def get_reassignment_detail(
    reassignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    reassignment = crud.get_reassignment(db, reassignment_id=reassignment_id)
    if not reassignment:
        raise HTTPException(status_code=404, detail="改派记录不存在")
    
    original_booking = None
    original_change = None
    original_occupancy = None
    
    if reassignment.booking_id:
        original_booking = reassignment.booking
    if reassignment.change_id:
        original_change = reassignment.change
    if reassignment.occupancy_id:
        original_occupancy = reassignment.occupancy
    
    adopted_solution = schemas.RecommendationItem(
        room=schemas.MeetingRoomResponse(
            id=reassignment.reassigned_room.id,
            name=reassignment.reassigned_room.name,
            capacity=reassignment.reassigned_room.capacity,
            location=reassignment.reassigned_room.location,
            description=reassignment.reassigned_room.description,
            is_active=reassignment.reassigned_room.is_active,
            equipments=[
                schemas.RoomEquipmentResponse(
                    id=re.id,
                    equipment_id=re.equipment_id,
                    quantity=re.quantity,
                    equipment=schemas.EquipmentResponse(
                        id=re.equipment.id,
                        name=re.equipment.name,
                        description=re.equipment.description
                    )
                ) for re in reassignment.reassigned_room.equipments
            ]
        ),
        start_time=reassignment.reassigned_start_time,
        end_time=reassignment.reassigned_end_time,
        match_score=reassignment.match_score or 0,
        reasons=reassignment.recommendation_reasons.split("; ") if reassignment.recommendation_reasons else [],
        is_same_room=(reassignment.original_room_id == reassignment.reassigned_room_id),
        is_same_time=(abs((reassignment.reassigned_start_time - reassignment.original_start_time).total_seconds()) < 60)
    )
    
    processing_status = "pending"
    if reassignment.status == "approved":
        processing_status = "approved"
    elif reassignment.status == "rejected":
        processing_status = "rejected"
    elif reassignment.status == "conflict":
        processing_status = "conflict"
    
    return schemas.ReassignmentWithDetailsResponse(
        reassignment=schemas.ReassignmentResponse(
            id=reassignment.id,
            booking_id=reassignment.booking_id,
            change_id=reassignment.change_id,
            occupancy_id=reassignment.occupancy_id,
            source_type=reassignment.source_type,
            original_room_id=reassignment.original_room_id,
            original_room=schemas.MeetingRoomResponse(
                id=reassignment.original_room.id,
                name=reassignment.original_room.name,
                capacity=reassignment.original_room.capacity,
                location=reassignment.original_room.location,
                description=reassignment.original_room.description,
                is_active=reassignment.original_room.is_active,
                equipments=[
                    schemas.RoomEquipmentResponse(
                        id=re.id,
                        equipment_id=re.equipment_id,
                        quantity=re.quantity,
                        equipment=schemas.EquipmentResponse(
                            id=re.equipment.id,
                            name=re.equipment.name,
                            description=re.equipment.description
                        )
                    ) for re in reassignment.original_room.equipments
                ]
            ) if reassignment.original_room else None,
            original_start_time=reassignment.original_start_time,
            original_end_time=reassignment.original_end_time,
            original_attendee_count=reassignment.original_attendee_count,
            reassigned_room_id=reassignment.reassigned_room_id,
            reassigned_room=schemas.MeetingRoomResponse(
                id=reassignment.reassigned_room.id,
                name=reassignment.reassigned_room.name,
                capacity=reassignment.reassigned_room.capacity,
                location=reassignment.reassigned_room.location,
                description=reassignment.reassigned_room.description,
                is_active=reassignment.reassigned_room.is_active,
                equipments=[
                    schemas.RoomEquipmentResponse(
                        id=re.id,
                        equipment_id=re.equipment_id,
                        quantity=re.quantity,
                        equipment=schemas.EquipmentResponse(
                            id=re.equipment.id,
                            name=re.equipment.name,
                            description=re.equipment.description
                        )
                    ) for re in reassignment.reassigned_room.equipments
                ]
            ) if reassignment.reassigned_room else None,
            reassigned_start_time=reassignment.reassigned_start_time,
            reassigned_end_time=reassignment.reassigned_end_time,
            reassigned_attendee_count=reassignment.reassigned_attendee_count,
            conflict_reasons=reassignment.conflict_reasons,
            recommendation_index=reassignment.recommendation_index,
            match_score=reassignment.match_score,
            recommendation_reasons=reassignment.recommendation_reasons,
            operator_id=reassignment.operator_id,
            operator=schemas.UserResponse(
                id=reassignment.operator.id,
                username=reassignment.operator.username,
                full_name=reassignment.operator.full_name,
                role=reassignment.operator.role,
                department_id=reassignment.operator.department_id,
                is_active=reassignment.operator.is_active
            ) if reassignment.operator else None,
            operated_at=reassignment.operated_at,
            processing_note=reassignment.processing_note,
            status=reassignment.status,
            reviewer_id=reassignment.reviewer_id,
            reviewer=schemas.UserResponse(
                id=reassignment.reviewer.id,
                username=reassignment.reviewer.username,
                full_name=reassignment.reviewer.full_name,
                role=reassignment.reviewer.role,
                department_id=reassignment.reviewer.department_id,
                is_active=reassignment.reviewer.is_active
            ) if reassignment.reviewer else None,
            review_time=reassignment.review_time,
            review_comment=reassignment.review_comment,
            equipment_diffs=[
                schemas.ReassignmentEquipmentDiffResponse(
                    id=diff.id,
                    equipment_id=diff.equipment_id,
                    old_quantity=diff.old_quantity,
                    new_quantity=diff.new_quantity,
                    diff_type=diff.diff_type,
                    equipment=schemas.EquipmentResponse(
                        id=diff.equipment.id,
                        name=diff.equipment.name,
                        description=diff.equipment.description
                    )
                ) for diff in reassignment.equipment_diffs
            ]
        ),
        original_booking=original_booking,
        original_change=original_change,
        original_occupancy=original_occupancy,
        adopted_solution=adopted_solution,
        processing_status=processing_status
    )


@router.post("/reassignments/{reassignment_id}/approve", response_model=schemas.ReassignmentResponse)
def approve_reassignment(
    reassignment_id: int,
    review_data: schemas.ReassignmentReviewRequest = schemas.ReassignmentReviewRequest(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    reassignment = crud.get_reassignment(db, reassignment_id=reassignment_id)
    if not reassignment:
        raise HTTPException(status_code=404, detail="改派记录不存在")
    if reassignment.status == "approved":
        raise HTTPException(status_code=400, detail="该改派已通过")
    if reassignment.status == "rejected":
        raise HTTPException(status_code=400, detail="该改派已被拒绝")
    updated = crud.review_reassignment(
        db,
        reassignment_id=reassignment_id,
        status="approved",
        reviewer_id=current_user.id,
        review_comment=review_data.review_comment
    )
    if not updated:
        raise HTTPException(status_code=500, detail="审核失败")
    return updated


@router.post("/reassignments/{reassignment_id}/reject", response_model=schemas.ReassignmentResponse)
def reject_reassignment(
    reassignment_id: int,
    review_data: schemas.ReassignmentReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    reassignment = crud.get_reassignment(db, reassignment_id=reassignment_id)
    if not reassignment:
        raise HTTPException(status_code=404, detail="改派记录不存在")
    if reassignment.status == "approved":
        raise HTTPException(status_code=400, detail="该改派已通过")
    if reassignment.status == "rejected":
        raise HTTPException(status_code=400, detail="该改派已被拒绝")
    if not review_data.review_comment:
        raise HTTPException(status_code=400, detail="拒绝时必须填写复核意见")
    updated = crud.review_reassignment(
        db,
        reassignment_id=reassignment_id,
        status="rejected",
        reviewer_id=current_user.id,
        review_comment=review_data.review_comment
    )
    if not updated:
        raise HTTPException(status_code=500, detail="审核失败")
    return updated
