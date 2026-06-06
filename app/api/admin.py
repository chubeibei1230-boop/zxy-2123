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
