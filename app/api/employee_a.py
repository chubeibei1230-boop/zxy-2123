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


def validate_booking_row(db: Session, row: dict, row_num: int) -> tuple[Optional[schemas.BookingCreate], list[str]]:
    errors = []
    required_fields = ["会议室名称", "会议标题", "参会人数", "部门名称", "开始日期", "开始时间", "结束日期", "结束时间"]
    for field in required_fields:
        if field not in row or not str(row[field]).strip():
            errors.append(f"缺少必填字段: {field}")
    if errors:
        return None, errors
    try:
        attendee_count = int(str(row["参会人数"]).strip())
    except ValueError:
        errors.append("参会人数必须是数字")
        attendee_count = 0
    room_name = str(row["会议室名称"]).strip()
    room = crud.get_meeting_room_by_name(db, name=room_name)
    if not room:
        errors.append(f"会议室不存在: {room_name}")
    dept_name = str(row["部门名称"]).strip()
    dept = crud.get_department_by_name(db, name=dept_name)
    if not dept:
        errors.append(f"部门不存在: {dept_name}")
    start_time = parse_datetime(str(row["开始日期"]), str(row["开始时间"]))
    end_time = parse_datetime(str(row["结束日期"]), str(row["结束时间"]))
    if not start_time:
        errors.append("开始时间格式错误，支持格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
    if not end_time:
        errors.append("结束时间格式错误，支持格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
    if start_time and end_time and start_time >= end_time:
        errors.append("结束时间必须晚于开始时间")
    if room and attendee_count > room.capacity:
        errors.append(f"参会人数({attendee_count})超过会议室容量({room.capacity})")
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
            else:
                room_eq = next((re for re in room.equipments if re.equipment_id == equip.id), None) if room else None
                if room and room_eq and qty > room_eq.quantity:
                    errors.append(f"设备 {eq_name} 数量不足，会议室最多提供 {room_eq.quantity} 个")
                else:
                    equipment_list.append(schemas.BookingEquipmentCreate(
                        equipment_id=equip.id,
                        quantity=qty
                    ))
    if errors:
        return None, errors
    booking = schemas.BookingCreate(
        room_id=room.id,
        title=str(row["会议标题"]).strip(),
        start_time=start_time,
        end_time=end_time,
        attendee_count=attendee_count,
        department_id=dept.id,
        equipments=equipment_list
    )
    return booking, []


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
    for row_num, row in enumerate(csv_reader, start=2):
        total_count += 1
        booking_create, errors = validate_booking_row(db, row, row_num)
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
            continue
        try:
            booking = crud.create_booking(
                db=db,
                booking=booking_create,
                applicant_id=current_user.id,
                batch_id=batch.id
            )
            success_count += 1
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
        successful_bookings=successful_bookings
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
        skip=skip,
        limit=limit
    )
