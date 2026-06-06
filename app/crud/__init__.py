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
