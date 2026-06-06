from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app import models, schemas
from app.core.security import get_password_hash


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_department(db: Session, dept_id: int) -> Optional[models.Department]:
    return db.query(models.Department).filter(models.Department.id == dept_id).first()


def get_department_by_name(db: Session, name: str) -> Optional[models.Department]:
    return db.query(models.Department).filter(models.Department.name == name).first()


def get_departments(db: Session, skip: int = 0, limit: int = 100) -> List[models.Department]:
    return db.query(models.Department).offset(skip).limit(limit).all()


def create_department(db: Session, dept: schemas.DepartmentCreate) -> models.Department:
    db_dept = models.Department(**dept.model_dump())
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept


def update_department(db: Session, dept_id: int, dept_update: schemas.DepartmentUpdate) -> Optional[models.Department]:
    db_dept = get_department(db, dept_id)
    if not db_dept:
        return None
    update_data = dept_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_dept, key, value)
    db.commit()
    db.refresh(db_dept)
    return db_dept


def get_equipment(db: Session, equip_id: int) -> Optional[models.Equipment]:
    return db.query(models.Equipment).filter(models.Equipment.id == equip_id).first()


def get_equipment_by_name(db: Session, name: str) -> Optional[models.Equipment]:
    return db.query(models.Equipment).filter(models.Equipment.name == name).first()


def get_equipments(db: Session, skip: int = 0, limit: int = 100) -> List[models.Equipment]:
    return db.query(models.Equipment).offset(skip).limit(limit).all()


def create_equipment(db: Session, equip: schemas.EquipmentCreate) -> models.Equipment:
    db_equip = models.Equipment(**equip.model_dump())
    db.add(db_equip)
    db.commit()
    db.refresh(db_equip)
    return db_equip


def update_equipment(db: Session, equip_id: int, equip_update: schemas.EquipmentUpdate) -> Optional[models.Equipment]:
    db_equip = get_equipment(db, equip_id)
    if not db_equip:
        return None
    update_data = equip_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_equip, key, value)
    db.commit()
    db.refresh(db_equip)
    return db_equip


def get_meeting_room(db: Session, room_id: int) -> Optional[models.MeetingRoom]:
    return db.query(models.MeetingRoom).filter(models.MeetingRoom.id == room_id).first()


def get_meeting_room_by_name(db: Session, name: str) -> Optional[models.MeetingRoom]:
    return db.query(models.MeetingRoom).filter(models.MeetingRoom.name == name).first()


def get_meeting_rooms(db: Session, skip: int = 0, limit: int = 100, only_active: bool = True) -> List[models.MeetingRoom]:
    query = db.query(models.MeetingRoom)
    if only_active:
        query = query.filter(models.MeetingRoom.is_active == True)
    return query.offset(skip).limit(limit).all()


def create_meeting_room(db: Session, room: schemas.MeetingRoomCreate) -> models.MeetingRoom:
    room_data = room.model_dump()
    equipments_data = room_data.pop("equipments", [])
    db_room = models.MeetingRoom(**room_data)
    db.add(db_room)
    db.flush()
    for eq_data in equipments_data:
        room_eq = models.RoomEquipment(
            room_id=db_room.id,
            equipment_id=eq_data["equipment_id"],
            quantity=eq_data.get("quantity", 1)
        )
        db.add(room_eq)
    db.commit()
    db.refresh(db_room)
    return db_room


def update_meeting_room(db: Session, room_id: int, room_update: schemas.MeetingRoomUpdate) -> Optional[models.MeetingRoom]:
    db_room = get_meeting_room(db, room_id)
    if not db_room:
        return None
    update_data = room_update.model_dump(exclude_unset=True)
    equipments_data = update_data.pop("equipments", None)
    for key, value in update_data.items():
        setattr(db_room, key, value)
    if equipments_data is not None:
        db.query(models.RoomEquipment).filter(models.RoomEquipment.room_id == room_id).delete()
        for eq_data in equipments_data:
            room_eq = models.RoomEquipment(
                room_id=room_id,
                equipment_id=eq_data["equipment_id"],
                quantity=eq_data.get("quantity", 1)
            )
            db.add(room_eq)
    db.commit()
    db.refresh(db_room)
    return db_room


def check_time_conflict(
    db: Session,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, List[str]]:
    conflicts = []
    booking_query = db.query(models.Booking).filter(
        models.Booking.room_id == room_id,
        models.Booking.status != "rejected",
        or_(
            and_(models.Booking.start_time < end_time, models.Booking.end_time > start_time)
        )
    )
    if exclude_booking_id:
        booking_query = booking_query.filter(models.Booking.id != exclude_booking_id)
    conflicting_bookings = booking_query.all()
    for b in conflicting_bookings:
        conflicts.append(f"预约冲突: {b.title} ({b.start_time.strftime('%Y-%m-%d %H:%M')} - {b.end_time.strftime('%Y-%m-%d %H:%M')})")
    occ_query = db.query(models.TemporaryOccupancy).filter(
        models.TemporaryOccupancy.room_id == room_id,
        or_(
            and_(models.TemporaryOccupancy.start_time < end_time, models.TemporaryOccupancy.end_time > start_time)
        )
    )
    conflicting_occs = occ_query.all()
    for o in conflicting_occs:
        conflicts.append(f"临时占用冲突: {o.title} ({o.start_time.strftime('%Y-%m-%d %H:%M')} - {o.end_time.strftime('%Y-%m-%d %H:%M')})")
    return len(conflicts) > 0, conflicts


def get_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def get_bookings(
    db: Session,
    room_id: Optional[int] = None,
    department_id: Optional[int] = None,
    applicant_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Booking]:
    query = db.query(models.Booking)
    if room_id:
        query = query.filter(models.Booking.room_id == room_id)
    if department_id:
        query = query.filter(models.Booking.department_id == department_id)
    if applicant_id:
        query = query.filter(models.Booking.applicant_id == applicant_id)
    if status:
        query = query.filter(models.Booking.status == status)
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    if end_date:
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(models.Booking.end_time <= end_date)
    return query.order_by(models.Booking.start_time.desc()).offset(skip).limit(limit).all()


def create_booking(db: Session, booking: schemas.BookingCreate, applicant_id: int, batch_id: Optional[int] = None) -> models.Booking:
    booking_data = booking.model_dump()
    equipments_data = booking_data.pop("equipments", [])
    db_booking = models.Booking(
        **booking_data,
        applicant_id=applicant_id,
        batch_id=batch_id,
        created_at=datetime.utcnow()
    )
    has_conflict, conflicts = check_time_conflict(db, booking.room_id, booking.start_time, booking.end_time)
    if has_conflict:
        db_booking.conflict_info = "; ".join(conflicts)
        db_booking.status = "conflict"
    db.add(db_booking)
    db.flush()
    for eq_data in equipments_data:
        booking_eq = models.BookingEquipment(
            booking_id=db_booking.id,
            equipment_id=eq_data["equipment_id"],
            quantity=eq_data.get("quantity", 1)
        )
        db.add(booking_eq)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def update_booking_status(
    db: Session,
    booking_id: int,
    status: str,
    reviewer_id: int,
    review_comment: Optional[str] = None
) -> Optional[models.Booking]:
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        return None
    db_booking.status = status
    db_booking.reviewer_id = reviewer_id
    db_booking.review_time = datetime.utcnow()
    if review_comment:
        db_booking.review_comment = review_comment
    db.commit()
    db.refresh(db_booking)
    return db_booking


def get_temporary_occupancy(db: Session, occ_id: int) -> Optional[models.TemporaryOccupancy]:
    return db.query(models.TemporaryOccupancy).filter(models.TemporaryOccupancy.id == occ_id).first()


def get_temporary_occupancies(
    db: Session,
    room_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.TemporaryOccupancy]:
    query = db.query(models.TemporaryOccupancy)
    if room_id:
        query = query.filter(models.TemporaryOccupancy.room_id == room_id)
    if start_date:
        query = query.filter(models.TemporaryOccupancy.start_time >= start_date)
    if end_date:
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(models.TemporaryOccupancy.end_time <= end_date)
    return query.order_by(models.TemporaryOccupancy.start_time.desc()).offset(skip).limit(limit).all()


def create_temporary_occupancy(
    db: Session,
    occ: schemas.TemporaryOccupancyCreate,
    created_by_id: int
) -> models.TemporaryOccupancy:
    db_occ = models.TemporaryOccupancy(
        **occ.model_dump(),
        created_by_id=created_by_id,
        created_at=datetime.utcnow()
    )
    db.add(db_occ)
    db.commit()
    db.refresh(db_occ)
    return db_occ


def delete_temporary_occupancy(db: Session, occ_id: int) -> bool:
    db_occ = get_temporary_occupancy(db, occ_id)
    if not db_occ:
        return False
    db.delete(db_occ)
    db.commit()
    return True


def create_import_batch(
    db: Session,
    batch_no: str,
    created_by_id: int,
    file_name: str
) -> models.ImportBatch:
    db_batch = models.ImportBatch(
        batch_no=batch_no,
        created_by_id=created_by_id,
        file_name=file_name,
        created_at=datetime.utcnow()
    )
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch


def add_import_error(
    db: Session,
    batch_id: int,
    row_number: int,
    error_type: str,
    error_message: str,
    row_data: Optional[str] = None
) -> models.ImportError:
    db_error = models.ImportError(
        batch_id=batch_id,
        row_number=row_number,
        error_type=error_type,
        error_message=error_message,
        row_data=row_data
    )
    db.add(db_error)
    db.commit()
    db.refresh(db_error)
    return db_error


def update_import_batch_stats(
    db: Session,
    batch_id: int,
    total_count: int,
    success_count: int,
    error_count: int,
    status: str = "completed"
) -> Optional[models.ImportBatch]:
    db_batch = db.query(models.ImportBatch).filter(models.ImportBatch.id == batch_id).first()
    if not db_batch:
        return None
    db_batch.total_count = total_count
    db_batch.success_count = success_count
    db_batch.error_count = error_count
    db_batch.status = status
    db.commit()
    db.refresh(db_batch)
    return db_batch


def get_import_batch(db: Session, batch_id: int) -> Optional[models.ImportBatch]:
    return db.query(models.ImportBatch).filter(models.ImportBatch.id == batch_id).first()


def get_import_batches(db: Session, skip: int = 0, limit: int = 100) -> List[models.ImportBatch]:
    return db.query(models.ImportBatch).order_by(models.ImportBatch.created_at.desc()).offset(skip).limit(limit).all()


def get_import_errors(db: Session, batch_id: int, skip: int = 0, limit: int = 1000) -> List[models.ImportError]:
    return db.query(models.ImportError).filter(models.ImportError.batch_id == batch_id).order_by(models.ImportError.row_number).offset(skip).limit(limit).all()


def get_occupancy_stats(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[dict]:
    rooms = get_meeting_rooms(db, only_active=True)
    stats = []
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow() + timedelta(days=30)
    total_period_hours = (end_date - start_date).total_seconds() / 3600
    for room in rooms:
        bookings = get_bookings(
            db,
            room_id=room.id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        approved = [b for b in bookings if b.status == "approved"]
        pending = [b for b in bookings if b.status == "pending" or b.status == "conflict"]
        rejected = [b for b in bookings if b.status == "rejected"]
        total_occupancy_hours = 0.0
        for b in approved:
            duration = (b.end_time - b.start_time).total_seconds() / 3600
            total_occupancy_hours += duration
        occupancy_rate = 0.0
        if total_period_hours > 0:
            occupancy_rate = (total_occupancy_hours / total_period_hours) * 100
        stats.append({
            "room_id": room.id,
            "room_name": room.name,
            "total_bookings": len(bookings),
            "total_occupancy_hours": round(total_occupancy_hours, 2),
            "pending_count": len(pending),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "occupancy_rate": round(occupancy_rate, 2)
        })
    return stats


def get_booking_rule(db: Session, rule_id: int) -> Optional[models.BookingRule]:
    return db.query(models.BookingRule).filter(models.BookingRule.id == rule_id).first()


def get_booking_rule_by_name(db: Session, rule_name: str) -> Optional[models.BookingRule]:
    return db.query(models.BookingRule).filter(models.BookingRule.rule_name == rule_name).first()


def get_active_booking_rule(db: Session) -> Optional[models.BookingRule]:
    return db.query(models.BookingRule).filter(models.BookingRule.is_active == True).first()


def get_booking_rules(db: Session, skip: int = 0, limit: int = 100) -> List[models.BookingRule]:
    return db.query(models.BookingRule).order_by(models.BookingRule.created_at.desc()).offset(skip).limit(limit).all()


def create_booking_rule(db: Session, rule: schemas.BookingRuleCreate) -> models.BookingRule:
    db_rule = models.BookingRule(
        **rule.model_dump(),
        created_at=datetime.utcnow()
    )
    if rule.is_active:
        db.query(models.BookingRule).update({models.BookingRule.is_active: False})
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


def update_booking_rule(db: Session, rule_id: int, rule_update: schemas.BookingRuleUpdate) -> Optional[models.BookingRule]:
    db_rule = get_booking_rule(db, rule_id)
    if not db_rule:
        return None
    update_data = rule_update.model_dump(exclude_unset=True)
    if update_data.get("is_active"):
        db.query(models.BookingRule).filter(models.BookingRule.id != rule_id).update({models.BookingRule.is_active: False})
    for key, value in update_data.items():
        setattr(db_rule, key, value)
    db.commit()
    db.refresh(db_rule)
    return db_rule


def delete_booking_rule(db: Session, rule_id: int) -> bool:
    db_rule = get_booking_rule(db, rule_id)
    if not db_rule:
        return False
    db.delete(db_rule)
    db.commit()
    return True


def validate_booking_modification(
    db: Session,
    booking: models.Booking,
    modify_data: schemas.BookingModifyRequest
) -> Tuple[bool, List[str], dict]:
    errors = []
    changes = {}

    new_room_id = modify_data.room_id if modify_data.room_id is not None else booking.room_id
    new_title = modify_data.title if modify_data.title is not None else booking.title
    new_start_time = modify_data.start_time if modify_data.start_time is not None else booking.start_time
    new_end_time = modify_data.end_time if modify_data.end_time is not None else booking.end_time
    new_attendee_count = modify_data.attendee_count if modify_data.attendee_count is not None else booking.attendee_count
    new_department_id = modify_data.department_id if modify_data.department_id is not None else booking.department_id

    room = get_meeting_room(db, room_id=new_room_id)
    if not room:
        errors.append("会议室不存在")
    else:
        if new_attendee_count > room.capacity:
            errors.append(f"参会人数({new_attendee_count})超过会议室容量({room.capacity})")

    department = get_department(db, dept_id=new_department_id)
    if not department:
        errors.append("部门不存在")

    if new_start_time >= new_end_time:
        errors.append("结束时间必须晚于开始时间")

    rule = get_active_booking_rule(db)
    if rule:
        from datetime import time
        start_time_only = new_start_time.time()
        end_time_only = new_end_time.time()
        rule_start = datetime.strptime(rule.start_time_limit, "%H:%M").time()
        rule_end = datetime.strptime(rule.end_time_limit, "%H:%M").time()
        if start_time_only < rule_start or end_time_only > rule_end:
            errors.append(f"预约时间需在 {rule.start_time_limit} - {rule.end_time_limit} 之间")
        
        if not rule.allow_weekend:
            if new_start_time.weekday() >= 5 or new_end_time.weekday() >= 5:
                errors.append("不允许周末预约")
        
        duration_hours = (new_end_time - new_start_time).total_seconds() / 3600
        if duration_hours < rule.min_booking_hours:
            errors.append(f"预约时长不足最短时长 {rule.min_booking_hours} 小时")
        if duration_hours > rule.max_booking_hours:
            errors.append(f"预约时长超过最长时长 {rule.max_booking_hours} 小时")
        
        days_ahead = (new_start_time.date() - datetime.utcnow().date()).days
        if days_ahead > rule.max_booking_days:
            errors.append(f"最多可提前 {rule.max_booking_days} 天预约")
        
        if rule.max_attendees_per_room and new_attendee_count > rule.max_attendees_per_room:
            errors.append(f"参会人数超过最大限制 {rule.max_attendees_per_room} 人")

    if modify_data.equipments is not None and room:
        for eq_req in modify_data.equipments:
            equip = get_equipment(db, equip_id=eq_req.equipment_id)
            if not equip:
                errors.append(f"设备ID {eq_req.equipment_id} 不存在")
                continue
            room_eq = next((re for re in room.equipments if re.equipment_id == equip.id), None)
            if not room_eq:
                errors.append(f"会议室 {room.name} 未配备设备: {equip.name}")
            elif eq_req.quantity > room_eq.quantity:
                errors.append(f"设备 {equip.name} 数量不足，会议室最多提供 {room_eq.quantity} 个")

    has_conflict, conflicts = check_time_conflict(
        db, new_room_id, new_start_time, new_end_time, exclude_booking_id=booking.id
    )
    if has_conflict:
        errors.extend(conflicts)

    if modify_data.room_id is not None and modify_data.room_id != booking.room_id:
        changes["room_id"] = {"old": booking.room_id, "new": modify_data.room_id}
    if modify_data.title is not None and modify_data.title != booking.title:
        changes["title"] = {"old": booking.title, "new": modify_data.title}
    if modify_data.start_time is not None and modify_data.start_time != booking.start_time:
        changes["start_time"] = {"old": booking.start_time, "new": modify_data.start_time}
    if modify_data.end_time is not None and modify_data.end_time != booking.end_time:
        changes["end_time"] = {"old": booking.end_time, "new": modify_data.end_time}
    if modify_data.attendee_count is not None and modify_data.attendee_count != booking.attendee_count:
        changes["attendee_count"] = {"old": booking.attendee_count, "new": modify_data.attendee_count}
    if modify_data.department_id is not None and modify_data.department_id != booking.department_id:
        changes["department_id"] = {"old": booking.department_id, "new": modify_data.department_id}

    if not changes and modify_data.equipments is None:
        errors.append("没有任何变更内容")

    return len(errors) == 0, errors, changes


def create_booking_change(
    db: Session,
    booking: models.Booking,
    modify_data: schemas.BookingModifyRequest,
    applicant_id: int
) -> models.BookingChange:
    db_change = models.BookingChange(
        booking_id=booking.id,
        applicant_id=applicant_id,
        old_room_id=booking.room_id,
        new_room_id=modify_data.room_id if modify_data.room_id is not None else booking.room_id,
        old_title=booking.title,
        new_title=modify_data.title if modify_data.title is not None else booking.title,
        old_start_time=booking.start_time,
        new_start_time=modify_data.start_time if modify_data.start_time is not None else booking.start_time,
        old_end_time=booking.end_time,
        new_end_time=modify_data.end_time if modify_data.end_time is not None else booking.end_time,
        old_attendee_count=booking.attendee_count,
        new_attendee_count=modify_data.attendee_count if modify_data.attendee_count is not None else booking.attendee_count,
        old_department_id=booking.department_id,
        new_department_id=modify_data.department_id if modify_data.department_id is not None else booking.department_id,
        change_reason=modify_data.change_reason,
        created_at=datetime.utcnow()
    )

    new_room_id = modify_data.room_id if modify_data.room_id is not None else booking.room_id
    new_start = modify_data.start_time if modify_data.start_time is not None else booking.start_time
    new_end = modify_data.end_time if modify_data.end_time is not None else booking.end_time

    has_conflict, conflicts = check_time_conflict(
        db, new_room_id, new_start, new_end, exclude_booking_id=booking.id
    )
    if has_conflict:
        db_change.conflict_info = "; ".join(conflicts)
        db_change.status = "conflict"
    else:
        db_change.status = "pending"

    db.add(db_change)
    db.flush()

    if modify_data.equipments is not None:
        old_equipments = {eq.equipment_id: eq.quantity for eq in booking.equipments}
        new_equipments = {eq.equipment_id: eq.quantity for eq in modify_data.equipments}
        all_equip_ids = set(old_equipments.keys()) | set(new_equipments.keys())
        
        for equip_id in all_equip_ids:
            old_qty = old_equipments.get(equip_id)
            new_qty = new_equipments.get(equip_id)
            if old_qty != new_qty:
                if old_qty is None:
                    change_type = "add"
                elif new_qty is None:
                    change_type = "remove"
                else:
                    change_type = "modify"
                db_eq_change = models.BookingEquipmentChange(
                    change_id=db_change.id,
                    equipment_id=equip_id,
                    old_quantity=old_qty,
                    new_quantity=new_qty,
                    change_type=change_type
                )
                db.add(db_eq_change)

    db.commit()
    db.refresh(db_change)
    return db_change


def get_booking_change(db: Session, change_id: int) -> Optional[models.BookingChange]:
    return db.query(models.BookingChange).filter(models.BookingChange.id == change_id).first()


def get_booking_changes(
    db: Session,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    applicant_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.BookingChange]:
    query = db.query(models.BookingChange)
    if booking_id:
        query = query.filter(models.BookingChange.booking_id == booking_id)
    if status:
        query = query.filter(models.BookingChange.status == status)
    if applicant_id:
        query = query.filter(models.BookingChange.applicant_id == applicant_id)
    return query.order_by(models.BookingChange.created_at.desc()).offset(skip).limit(limit).all()


def review_booking_change(
    db: Session,
    change_id: int,
    status: str,
    reviewer_id: int,
    review_comment: Optional[str] = None
) -> Optional[models.BookingChange]:
    db_change = get_booking_change(db, change_id)
    if not db_change:
        return None
    if db_change.status not in ["pending", "conflict"]:
        return None
    
    db_change.status = status
    db_change.reviewer_id = reviewer_id
    db_change.review_time = datetime.utcnow()
    if review_comment:
        db_change.review_comment = review_comment
    
    if status == "approved":
        booking = db_change.booking
        booking.room_id = db_change.new_room_id
        booking.title = db_change.new_title
        booking.start_time = db_change.new_start_time
        booking.end_time = db_change.new_end_time
        booking.attendee_count = db_change.new_attendee_count
        booking.department_id = db_change.new_department_id
        booking.is_modified = True
        booking.last_modified_at = datetime.utcnow()
        
        if db_change.equipment_changes:
            db.query(models.BookingEquipment).filter(models.BookingEquipment.booking_id == booking.id).delete()
            new_equipments = {}
            old_equipments = {eq.equipment_id: eq.quantity for eq in booking.equipments}
            for eq_change in db_change.equipment_changes:
                if eq_change.change_type == "add":
                    new_equipments[eq_change.equipment_id] = eq_change.new_quantity
                elif eq_change.change_type == "remove":
                    pass
                elif eq_change.change_type == "modify":
                    new_equipments[eq_change.equipment_id] = eq_change.new_quantity
            for equip_id, qty in old_equipments.items():
                if equip_id not in new_equipments:
                    has_remove = any(ec.equipment_id == equip_id and ec.change_type == "remove" for ec in db_change.equipment_changes)
                    if not has_remove:
                        new_equipments[equip_id] = qty
            for equip_id, qty in new_equipments.items():
                if qty is not None:
                    booking_eq = models.BookingEquipment(
                        booking_id=booking.id,
                        equipment_id=equip_id,
                        quantity=qty
                    )
                    db.add(booking_eq)
    
    db.commit()
    db.refresh(db_change)
    return db_change


def cancel_booking(
    db: Session,
    booking_id: int,
    cancelled_by_id: int,
    cancel_reason: str
) -> Optional[models.Booking]:
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        return None
    if db_booking.is_cancelled:
        return None
    db_booking.is_cancelled = True
    db_booking.cancelled_by_id = cancelled_by_id
    db_booking.cancelled_at = datetime.utcnow()
    db_booking.cancel_reason = cancel_reason
    db.commit()
    db.refresh(db_booking)
    return db_booking


def get_bookings(
    db: Session,
    room_id: Optional[int] = None,
    department_id: Optional[int] = None,
    applicant_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_cancelled: Optional[bool] = None,
    is_modified: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Booking]:
    query = db.query(models.Booking)
    if room_id:
        query = query.filter(models.Booking.room_id == room_id)
    if department_id:
        query = query.filter(models.Booking.department_id == department_id)
    if applicant_id:
        query = query.filter(models.Booking.applicant_id == applicant_id)
    if status:
        query = query.filter(models.Booking.status == status)
    if start_date:
        query = query.filter(models.Booking.start_time >= start_date)
    if end_date:
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(models.Booking.end_time <= end_date)
    if is_cancelled is not None:
        query = query.filter(models.Booking.is_cancelled == is_cancelled)
    if is_modified is not None:
        query = query.filter(models.Booking.is_modified == is_modified)
    return query.order_by(models.Booking.start_time.desc()).offset(skip).limit(limit).all()


def get_occupancy_stats(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[dict]:
    rooms = get_meeting_rooms(db, only_active=True)
    stats = []
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow() + timedelta(days=30)
    total_period_hours = (end_date - start_date).total_seconds() / 3600
    for room in rooms:
        bookings = get_bookings(
            db,
            room_id=room.id,
            start_date=start_date,
            end_date=end_date,
            is_cancelled=False,
            limit=10000
        )
        approved = [b for b in bookings if b.status == "approved"]
        pending = [b for b in bookings if b.status == "pending" or b.status == "conflict"]
        rejected = [b for b in bookings if b.status == "rejected"]
        modified = [b for b in bookings if b.is_modified]
        total_occupancy_hours = 0.0
        for b in approved:
            duration = (b.end_time - b.start_time).total_seconds() / 3600
            total_occupancy_hours += duration
        occupancy_rate = 0.0
        if total_period_hours > 0:
            occupancy_rate = (total_occupancy_hours / total_period_hours) * 100
        stats.append({
            "room_id": room.id,
            "room_name": room.name,
            "total_bookings": len(bookings),
            "total_occupancy_hours": round(total_occupancy_hours, 2),
            "pending_count": len(pending),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "modified_count": len(modified),
            "occupancy_rate": round(occupancy_rate, 2)
        })
    return stats
