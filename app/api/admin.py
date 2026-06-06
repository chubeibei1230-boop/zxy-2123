from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import require_role
from app.core.recommendation import generate_recommendations, check_room_equipment_match

router = APIRouter(prefix="/admin", tags=["管理员"], dependencies=[Depends(require_role(["admin"]))])


@router.get("/departments", response_model=List[schemas.DepartmentResponse])
def list_departments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_departments(db, skip=skip, limit=limit)


@router.post("/departments", response_model=schemas.DepartmentResponse)
def create_department(dept: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    existing = crud.get_department_by_name(db, name=dept.name)
    if existing:
        raise HTTPException(status_code=400, detail="部门名称已存在")
    return crud.create_department(db=db, dept=dept)


@router.get("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    dept = crud.get_department(db, dept_id=dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    return dept


@router.put("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
def update_department(dept_id: int, dept_update: schemas.DepartmentUpdate, db: Session = Depends(get_db)):
    if dept_update.name:
        existing = crud.get_department_by_name(db, name=dept_update.name)
        if existing and existing.id != dept_id:
            raise HTTPException(status_code=400, detail="部门名称已存在")
    dept = crud.update_department(db, dept_id=dept_id, dept_update=dept_update)
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    return dept


@router.get("/equipments", response_model=List[schemas.EquipmentResponse])
def list_equipments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_equipments(db, skip=skip, limit=limit)


@router.post("/equipments", response_model=schemas.EquipmentResponse)
def create_equipment(equip: schemas.EquipmentCreate, db: Session = Depends(get_db)):
    existing = crud.get_equipment_by_name(db, name=equip.name)
    if existing:
        raise HTTPException(status_code=400, detail="设备名称已存在")
    return crud.create_equipment(db=db, equip=equip)


@router.get("/equipments/{equip_id}", response_model=schemas.EquipmentResponse)
def get_equipment(equip_id: int, db: Session = Depends(get_db)):
    equip = crud.get_equipment(db, equip_id=equip_id)
    if not equip:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equip


@router.put("/equipments/{equip_id}", response_model=schemas.EquipmentResponse)
def update_equipment(equip_id: int, equip_update: schemas.EquipmentUpdate, db: Session = Depends(get_db)):
    if equip_update.name:
        existing = crud.get_equipment_by_name(db, name=equip_update.name)
        if existing and existing.id != equip_id:
            raise HTTPException(status_code=400, detail="设备名称已存在")
    equip = crud.update_equipment(db, equip_id=equip_id, equip_update=equip_update)
    if not equip:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equip


@router.get("/rooms", response_model=List[schemas.MeetingRoomResponse])
def list_meeting_rooms(skip: int = 0, limit: int = 100, only_active: bool = True, db: Session = Depends(get_db)):
    return crud.get_meeting_rooms(db, skip=skip, limit=limit, only_active=only_active)


@router.post("/rooms", response_model=schemas.MeetingRoomResponse)
def create_meeting_room(room: schemas.MeetingRoomCreate, db: Session = Depends(get_db)):
    existing = crud.get_meeting_room_by_name(db, name=room.name)
    if existing:
        raise HTTPException(status_code=400, detail="会议室名称已存在")
    for eq in room.equipments:
        equip = crud.get_equipment(db, equip_id=eq.equipment_id)
        if not equip:
            raise HTTPException(status_code=400, detail=f"设备ID {eq.equipment_id} 不存在")
    return crud.create_meeting_room(db=db, room=room)


@router.get("/rooms/{room_id}", response_model=schemas.MeetingRoomResponse)
def get_meeting_room(room_id: int, db: Session = Depends(get_db)):
    room = crud.get_meeting_room(db, room_id=room_id)
    if not room:
        raise HTTPException(status_code=404, detail="会议室不存在")
    return room


@router.put("/rooms/{room_id}", response_model=schemas.MeetingRoomResponse)
def update_meeting_room(room_id: int, room_update: schemas.MeetingRoomUpdate, db: Session = Depends(get_db)):
    if room_update.name:
        existing = crud.get_meeting_room_by_name(db, name=room_update.name)
        if existing and existing.id != room_id:
            raise HTTPException(status_code=400, detail="会议室名称已存在")
    if room_update.equipments:
        for eq in room_update.equipments:
            equip = crud.get_equipment(db, equip_id=eq.equipment_id)
            if not equip:
                raise HTTPException(status_code=400, detail=f"设备ID {eq.equipment_id} 不存在")
    room = crud.update_meeting_room(db, room_id=room_id, room_update=room_update)
    if not room:
        raise HTTPException(status_code=404, detail="会议室不存在")
    return room


@router.post("/occupancies", response_model=schemas.OccupancyWithRecommendationResponse)
def create_temporary_occupancy(
    occ: schemas.TemporaryOccupancyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    errors = []
    room = crud.get_meeting_room(db, room_id=occ.room_id)
    if not room:
        errors.append("会议室不存在")
    if occ.start_time >= occ.end_time:
        errors.append("结束时间必须晚于开始时间")
    
    attendee_count = getattr(occ, 'attendee_count', 0) or 0
    required_equipments = getattr(occ, 'equipments', []) or []
    
    if room:
        if attendee_count > 0 and attendee_count > room.capacity:
            errors.append(f"会议室容量不足(需要{attendee_count}人，仅容纳{room.capacity}人)")
        
        if required_equipments:
            equip_ok, equip_issues = check_room_equipment_match(db, room, required_equipments)
            if not equip_ok:
                errors.extend(equip_issues)
    
    has_conflict = False
    conflicts = []
    if room:
        has_conflict, conflicts = crud.check_time_conflict(db, occ.room_id, occ.start_time, occ.end_time)
        if has_conflict:
            errors.append("时间冲突: " + "; ".join(conflicts))
    
    if errors:
        if room:
            recommendations = generate_recommendations(
                db=db,
                original_room_id=occ.room_id,
                original_start=occ.start_time,
                original_end=occ.end_time,
                attendee_count=attendee_count if attendee_count > 0 else 1,
                department_id=None,
                required_equipments=required_equipments,
                max_recommendations=5,
                title_keywords=getattr(occ, 'reason', None),
                check_capacity=(attendee_count > 0),
                check_equipment=(len(required_equipments) > 0)
            )
            return schemas.OccupancyWithRecommendationResponse(
                success=False,
                errors=errors,
                recommendations=recommendations
            )
        return schemas.OccupancyWithRecommendationResponse(
            success=False,
            errors=errors
        )
    
    occupancy = crud.create_temporary_occupancy(db=db, occ=occ, created_by_id=current_user.id)
    return schemas.OccupancyWithRecommendationResponse(
        success=True,
        occupancy=occupancy
    )


@router.delete("/occupancies/{occ_id}")
def delete_temporary_occupancy(occ_id: int, db: Session = Depends(get_db)):
    success = crud.delete_temporary_occupancy(db, occ_id=occ_id)
    if not success:
        raise HTTPException(status_code=404, detail="临时占用不存在")
    return {"message": "删除成功"}


@router.get("/booking-rules", response_model=List[schemas.BookingRuleResponse])
def list_booking_rules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_booking_rules(db, skip=skip, limit=limit)


@router.get("/booking-rules/active", response_model=Optional[schemas.BookingRuleResponse])
def get_active_booking_rule(db: Session = Depends(get_db)):
    return crud.get_active_booking_rule(db)


@router.post("/booking-rules", response_model=schemas.BookingRuleResponse)
def create_booking_rule(rule: schemas.BookingRuleCreate, db: Session = Depends(get_db)):
    existing = crud.get_booking_rule_by_name(db, rule_name=rule.rule_name)
    if existing:
        raise HTTPException(status_code=400, detail="规则名称已存在")
    return crud.create_booking_rule(db=db, rule=rule)


@router.get("/booking-rules/{rule_id}", response_model=schemas.BookingRuleResponse)
def get_booking_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = crud.get_booking_rule(db, rule_id=rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="预约规则不存在")
    return rule


@router.put("/booking-rules/{rule_id}", response_model=schemas.BookingRuleResponse)
def update_booking_rule(rule_id: int, rule_update: schemas.BookingRuleUpdate, db: Session = Depends(get_db)):
    if rule_update.rule_name:
        existing = crud.get_booking_rule_by_name(db, rule_name=rule_update.rule_name)
        if existing and existing.id != rule_id:
            raise HTTPException(status_code=400, detail="规则名称已存在")
    rule = crud.update_booking_rule(db, rule_id=rule_id, rule_update=rule_update)
    if not rule:
        raise HTTPException(status_code=404, detail="预约规则不存在")
    return rule


@router.delete("/booking-rules/{rule_id}")
def delete_booking_rule(rule_id: int, db: Session = Depends(get_db)):
    success = crud.delete_booking_rule(db, rule_id=rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="预约规则不存在")
    return {"message": "删除成功"}


@router.post("/occupancies/reassign", response_model=schemas.ReassignmentWithDetailsResponse)
def reassign_occupancy(
    request: schemas.ReassignmentSelectRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    if request.occupancy_id:
        occupancy = crud.get_temporary_occupancy(db, occ_id=request.occupancy_id)
        if not occupancy:
            raise HTTPException(status_code=404, detail="临时占用不存在")
    
    reassignment = crud.create_reassignment(db, request, operator_id=current_user.id)
    
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
        processing_status="reassigned_pending_review" if reassignment.status == "pending" else "reassigned_with_conflict"
    )


@router.get("/reassignments", response_model=List[schemas.ReassignmentResponse])
def list_reassignments(
    booking_id: Optional[int] = None,
    change_id: Optional[int] = None,
    status: Optional[str] = None,
    operator_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    return crud.get_reassignments(
        db,
        booking_id=booking_id,
        change_id=change_id,
        status=status,
        operator_id=operator_id,
        skip=skip,
        limit=limit
    )
