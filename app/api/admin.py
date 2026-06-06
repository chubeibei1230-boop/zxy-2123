from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import require_role

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


@router.post("/occupancies", response_model=schemas.TemporaryOccupancyResponse)
def create_temporary_occupancy(
    occ: schemas.TemporaryOccupancyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_b"]))
):
    room = crud.get_meeting_room(db, room_id=occ.room_id)
    if not room:
        raise HTTPException(status_code=400, detail="会议室不存在")
    if occ.start_time >= occ.end_time:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    return crud.create_temporary_occupancy(db=db, occ=occ, created_by_id=current_user.id)


@router.delete("/occupancies/{occ_id}")
def delete_temporary_occupancy(occ_id: int, db: Session = Depends(get_db)):
    success = crud.delete_temporary_occupancy(db, occ_id=occ_id)
    if not success:
        raise HTTPException(status_code=404, detail="临时占用不存在")
    return {"message": "删除成功"}
