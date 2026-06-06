import csv
import io
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, crud, models
from app.core.database import get_db
from app.core.security import require_role
from app.core.recommendation import generate_recommendations

router = APIRouter(prefix="/employee-a", tags=["员工A-预约导入"], dependencies=[Depends(require_role(["admin", "employee_a"]))])


def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    combined = f"{date_str.strip()} {time_str.strip()}"
    for fmt in formats:
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    return None


def validate_booking_row(db: Session, row: dict, row_num: int) -> tuple[Optional[schemas.BookingCreate], list[str], dict]:
    errors = []
    context = {
        "room": None,
        "dept": None,
        "start_time": None,
        "end_time": None,
        "attendee_count": 0,
        "equipments": []
    }
    required_fields = ["会议室名称", "会议标题", "参会人数", "部门名称", "开始日期", "开始时间", "结束日期", "结束时间"]
    for field in required_fields:
        if field not in row or not str(row[field]).strip():
            errors.append(f"缺少必填字段: {field}")
    if errors:
        return None, errors, context
    try:
        attendee_count = int(str(row["参会人数"]).strip())
    except ValueError:
        errors.append("参会人数必须是数字")
        attendee_count = 0
    context["attendee_count"] = attendee_count
    room_name = str(row["会议室名称"]).strip()
    room = crud.get_meeting_room_by_name(db, name=room_name)
    if not room:
        errors.append(f"会议室不存在: {room_name}")
    else:
        context["room"] = room
    dept_name = str(row["部门名称"]).strip()
    dept = crud.get_department_by_name(db, name=dept_name)
    if not dept:
        errors.append(f"部门不存在: {dept_name}")
    else:
        context["dept"] = dept
    start_time = parse_datetime(str(row["开始日期"]), str(row["开始时间"]))
    end_time = parse_datetime(str(row["结束日期"]), str(row["结束时间"]))
    if not start_time:
        errors.append("开始时间格式错误，支持格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
    else:
        context["start_time"] = start_time
    if not end_time:
        errors.append("结束时间格式错误，支持格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
    else:
        context["end_time"] = end_time
    if start_time and end_time and start_time >= end_time:
        errors.append("结束时间必须晚于开始时间")
    if room and attendee_count > room.capacity:
        errors.append(f"参会人数({attendee_count})超过会议室容量({room.capacity})")
    
    rule = crud.get_active_booking_rule(db)
    if rule and start_time and end_time:
        start_time_only = start_time.time()
        end_time_only = end_time.time()
        rule_start = datetime.strptime(rule.start_time_limit, "%H:%M").time()
        rule_end = datetime.strptime(rule.end_time_limit, "%H:%M").time()
        if start_time_only < rule_start or end_time_only > rule_end:
            errors.append(f"预约时间需在 {rule.start_time_limit} - {rule.end_time_limit} 之间")
        
        if not rule.allow_weekend:
            if start_time.weekday() >= 5 or end_time.weekday() >= 5:
                errors.append("不允许周末预约")
        
        duration_hours = (end_time - start_time).total_seconds() / 3600
        if duration_hours < rule.min_booking_hours:
            errors.append(f"预约时长不足最短时长 {rule.min_booking_hours} 小时")
        if duration_hours > rule.max_booking_hours:
            errors.append(f"预约时长超过最长时长 {rule.max_booking_hours} 小时")
        
        days_ahead = (start_time.date() - datetime.utcnow().date()).days
        if days_ahead > rule.max_booking_days:
            errors.append(f"最多可提前 {rule.max_booking_days} 天预约")
        
        if rule.max_attendees_per_room and attendee_count > rule.max_attendees_per_room:
            errors.append(f"参会人数超过最大限制 {rule.max_attendees_per_room} 人")
    
    equipment_list = []
    if "设备需求" in row and str(row["设备需求"]).strip():
        equip_str = str(row["设备需求"]).strip()
        equip_items = [item.strip() for item in equip_str.split(";") if item.strip()]
        for item in equip_items:
            parts = item.split("*")
            eq_name = parts[0].strip()
            qty = 1
            if len(parts) > 1:
                try:
                    qty = int(parts[1].strip())
                except ValueError:
                    errors.append(f"设备数量格式错误: {item}")
                    continue
            equip = crud.get_equipment_by_name(db, name=eq_name)
            if not equip:
                errors.append(f"设备不存在: {eq_name}")
            elif not room:
                errors.append(f"会议室不存在，无法检查设备 {eq_name}")
            else:
                room_eq = next((re for re in room.equipments if re.equipment_id == equip.id), None)
                if not room_eq:
                    errors.append(f"会议室 {room.name} 未配备设备: {eq_name}")
                elif qty > room_eq.quantity:
                    errors.append(f"设备 {eq_name} 数量不足，会议室最多提供 {room_eq.quantity} 个")
                else:
                    equipment_list.append(schemas.BookingEquipmentCreate(
                        equipment_id=equip.id,
                        quantity=qty
                    ))
    context["equipments"] = equipment_list
    if errors:
        return None, errors, context
    booking = schemas.BookingCreate(
        room_id=room.id,
        title=str(row["会议标题"]).strip(),
        start_time=start_time,
        end_time=end_time,
        attendee_count=attendee_count,
        department_id=dept.id,
        equipments=equipment_list
    )
    return booking, [], context


@router.post("/import-bookings", response_model=schemas.ImportResultResponse)
async def import_bookings(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_a"]))
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件")
    content = await file.read()
    try:
        csv_content = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            csv_content = content.decode('gbk')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码格式不支持，请使用UTF-8或GBK编码")
    batch_no = f"BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    batch = crud.create_import_batch(
        db=db,
        batch_no=batch_no,
        created_by_id=current_user.id,
        file_name=file.filename
    )
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    total_count = 0
    success_count = 0
    error_count = 0
    successful_bookings = []
    failed_rows = []
    for row_num, row in enumerate(csv_reader, start=2):
        total_count += 1
        booking_create, errors, context = validate_booking_row(db, row, row_num)
        
        row_result = schemas.ImportRowResult(
            row_number=row_num,
            success=False,
            errors=errors
        )
        
        if errors:
            error_count += 1
            crud.add_import_error(
                db=db,
                batch_id=batch.id,
                row_number=row_num,
                error_type="数据校验错误",
                error_message="; ".join(errors),
                row_data=str(row)
            )
            
            if context["room"] and context["start_time"] and context["end_time"]:
                recommendations = generate_recommendations(
                    db=db,
                    original_room_id=context["room"].id,
                    original_start=context["start_time"],
                    original_end=context["end_time"],
                    attendee_count=context["attendee_count"],
                    department_id=context["dept"].id if context["dept"] else None,
                    required_equipments=context["equipments"],
                    max_recommendations=5
                )
                row_result.recommendations = recommendations
            
            failed_rows.append(row_result)
            continue
        
        try:
            booking = crud.create_booking(
                db=db,
                booking=booking_create,
                applicant_id=current_user.id,
                batch_id=batch.id
            )
            success_count += 1
            
            if booking.status == "conflict":
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
                row_result.success = True
                row_result.booking = booking
                row_result.recommendations = recommendations
                failed_rows.append(row_result)
                successful_bookings.append(booking)
            else:
                successful_bookings.append(booking)
        except Exception as e:
            error_count += 1
            crud.add_import_error(
                db=db,
                batch_id=batch.id,
                row_number=row_num,
                error_type="系统错误",
                error_message=str(e),
                row_data=str(row)
            )
            if context["room"] and context["start_time"] and context["end_time"]:
                recommendations = generate_recommendations(
                    db=db,
                    original_room_id=context["room"].id,
                    original_start=context["start_time"],
                    original_end=context["end_time"],
                    attendee_count=context["attendee_count"],
                    department_id=context["dept"].id if context["dept"] else None,
                    required_equipments=context["equipments"],
                    max_recommendations=5,
                    title_keywords=row.get("会议标题", "")
                )
                row_result.recommendations = recommendations
            failed_rows.append(row_result)
    batch = crud.update_import_batch_stats(
        db=db,
        batch_id=batch.id,
        total_count=total_count,
        success_count=success_count,
        error_count=error_count,
        status="completed"
    )
    return schemas.ImportResultResponse(
        batch=batch,
        successful_bookings=successful_bookings,
        failed_rows=failed_rows
    )


@router.get("/batches", response_model=List[schemas.ImportBatchResponse])
def list_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_import_batches(db, skip=skip, limit=limit)


@router.get("/batches/{batch_id}", response_model=schemas.ImportBatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = crud.get_import_batch(db, batch_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return batch


@router.get("/batches/{batch_id}/errors", response_model=List[schemas.ImportErrorResponse])
def get_batch_errors(batch_id: int, skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    batch = crud.get_import_batch(db, batch_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return crud.get_import_errors(db, batch_id=batch_id, skip=skip, limit=limit)


@router.get("/my-bookings", response_model=List[schemas.BookingResponse])
def get_my_bookings(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_cancelled: Optional[bool] = None,
    is_modified: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_a"]))
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
    return crud.get_bookings(
        db,
        applicant_id=current_user.id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        is_cancelled=is_cancelled,
        is_modified=is_modified,
        skip=skip,
        limit=limit
    )


@router.post("/bookings/{booking_id}/modify", response_model=schemas.BookingChangeWithRecommendationResponse)
def modify_booking(
    booking_id: int,
    modify_data: schemas.BookingModifyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_a"]))
):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        return schemas.BookingChangeWithRecommendationResponse(
            success=False,
            errors=["预约不存在"]
        )
    if booking.applicant_id != current_user.id and current_user.role != "admin":
        return schemas.BookingChangeWithRecommendationResponse(
            success=False,
            errors=["无权修改他人的预约"]
        )
    if booking.is_cancelled:
        return schemas.BookingChangeWithRecommendationResponse(
            success=False,
            errors=["已取消的预约无法修改"]
        )
    if booking.end_time < datetime.utcnow():
        return schemas.BookingChangeWithRecommendationResponse(
            success=False,
            errors=["已结束的预约无法修改"]
        )
    
    is_valid, errors, changes, conflicts = crud.validate_booking_modification(db, booking, modify_data)
    
    if not is_valid or conflicts:
        new_room_id = modify_data.room_id if modify_data.room_id is not None else booking.room_id
        new_start = modify_data.start_time if modify_data.start_time is not None else booking.start_time
        new_end = modify_data.end_time if modify_data.end_time is not None else booking.end_time
        new_attendee = modify_data.attendee_count if modify_data.attendee_count is not None else booking.attendee_count
        new_dept = modify_data.department_id if modify_data.department_id is not None else booking.department_id
        new_equipments = modify_data.equipments if modify_data.equipments is not None else [
            schemas.BookingEquipmentCreate(equipment_id=eq.equipment_id, quantity=eq.quantity)
            for eq in booking.equipments
        ]
        
        recommendations = generate_recommendations(
            db=db,
            original_room_id=new_room_id,
            original_start=new_start,
            original_end=new_end,
            attendee_count=new_attendee,
            department_id=new_dept,
            required_equipments=new_equipments,
            exclude_booking_id=booking.id,
            max_recommendations=5,
            title_keywords=modify_data.title if modify_data.title else booking.title
        )
        
        return schemas.BookingChangeWithRecommendationResponse(
            success=False,
            errors=errors + conflicts,
            recommendations=recommendations
        )
    
    booking_change = crud.create_booking_change(db, booking, modify_data, current_user.id)
    
    if booking_change.status == "conflict":
        new_room_id = modify_data.room_id if modify_data.room_id is not None else booking.room_id
        new_start = modify_data.start_time if modify_data.start_time is not None else booking.start_time
        new_end = modify_data.end_time if modify_data.end_time is not None else booking.end_time
        new_attendee = modify_data.attendee_count if modify_data.attendee_count is not None else booking.attendee_count
        new_dept = modify_data.department_id if modify_data.department_id is not None else booking.department_id
        new_equipments = modify_data.equipments if modify_data.equipments is not None else [
            schemas.BookingEquipmentCreate(equipment_id=eq.equipment_id, quantity=eq.quantity)
            for eq in booking.equipments
        ]
        
        recommendations = generate_recommendations(
            db=db,
            original_room_id=new_room_id,
            original_start=new_start,
            original_end=new_end,
            attendee_count=new_attendee,
            department_id=new_dept,
            required_equipments=new_equipments,
            exclude_booking_id=booking.id,
            max_recommendations=5,
            title_keywords=modify_data.title if modify_data.title else booking.title
        )
        
        return schemas.BookingChangeWithRecommendationResponse(
            success=True,
            change=booking_change,
            recommendations=recommendations
        )
    
    return schemas.BookingChangeWithRecommendationResponse(
        success=True,
        change=booking_change
    )


@router.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingResponse)
def cancel_booking(
    booking_id: int,
    cancel_data: schemas.BookingCancelRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_a"]))
):
    booking = crud.get_booking(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权取消他人的预约")
    if booking.is_cancelled:
        raise HTTPException(status_code=400, detail="该预约已取消")
    if booking.end_time < datetime.utcnow():
        raise HTTPException(status_code=400, detail="已结束的预约无法取消")
    
    updated = crud.cancel_booking(
        db,
        booking_id=booking_id,
        cancelled_by_id=current_user.id,
        cancel_reason=cancel_data.cancel_reason
    )
    if not updated:
        raise HTTPException(status_code=500, detail="取消预约失败")
    return updated


@router.get("/my-changes", response_model=List[schemas.BookingChangeResponse])
def get_my_changes(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "employee_a"]))
):
    return crud.get_booking_changes(
        db,
        applicant_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )
