from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app import models, schemas, crud


def check_room_equipment_match(
    db: Session,
    room: models.MeetingRoom,
    required_equipments: List[schemas.BookingEquipmentCreate]
) -> Tuple[bool, List[str]]:
    if not required_equipments:
        return True, []
    
    missing = []
    insufficient = []
    room_equip_map = {re.equipment_id: re for re in room.equipments}
    
    for req in required_equipments:
        if req.equipment_id not in room_equip_map:
            equip = crud.get_equipment(db, req.equipment_id)
            equip_name = equip.name if equip else f"设备{req.equipment_id}"
            missing.append(equip_name)
        else:
            room_eq = room_equip_map[req.equipment_id]
            if req.quantity > room_eq.quantity:
                equip = crud.get_equipment(db, req.equipment_id)
                equip_name = equip.name if equip else f"设备{req.equipment_id}"
                insufficient.append(f"{equip_name}(需要{req.quantity}个，现有{room_eq.quantity}个)")
    
    reasons = []
    if missing:
        reasons.append(f"缺少设备: {', '.join(missing)}")
    if insufficient:
        reasons.append(f"设备数量不足: {', '.join(insufficient)}")
    
    return len(reasons) == 0, reasons


def get_available_time_slots(
    db: Session,
    room: models.MeetingRoom,
    desired_start: datetime,
    desired_end: datetime,
    duration_minutes: int,
    exclude_booking_id: Optional[int] = None,
    max_slots_per_direction: int = 3
) -> List[Tuple[datetime, datetime, List[str]]]:
    slots = []
    booking_rule = crud.get_active_booking_rule(db)
    
    def is_within_rules(start: datetime, end: datetime) -> Tuple[bool, List[str]]:
        reasons = []
        if booking_rule:
            from datetime import time
            start_time_only = start.time()
            end_time_only = end.time()
            rule_start = datetime.strptime(booking_rule.start_time_limit, "%H:%M").time()
            rule_end = datetime.strptime(booking_rule.end_time_limit, "%H:%M").time()
            
            if start_time_only < rule_start or end_time_only > rule_end:
                reasons.append(f"超出工作时间范围 {booking_rule.start_time_limit}-{booking_rule.end_time_limit}")
            
            if not booking_rule.allow_weekend:
                if start.weekday() >= 5 or end.weekday() >= 5:
                    reasons.append("不支持周末预约")
            
            duration_hours = (end - start).total_seconds() / 3600
            if duration_hours < booking_rule.min_booking_hours:
                reasons.append(f"时长不足最短{booking_rule.min_booking_hours}小时")
            if duration_hours > booking_rule.max_booking_hours:
                reasons.append(f"时长超过最长{booking_rule.max_booking_hours}小时")
            
            days_ahead = (start.date() - datetime.utcnow().date()).days
            if days_ahead > booking_rule.max_booking_days:
                reasons.append(f"超过提前预约天数限制{booking_rule.max_booking_days}天")
        
        return len(reasons) == 0, reasons
    
    def check_and_add_slot(start: datetime, end: datetime, base_reasons: List[str]):
        has_conflict, conflicts = crud.check_time_conflict(
            db, room.id, start, end, exclude_booking_id=exclude_booking_id
        )
        if not has_conflict:
            valid, rule_reasons = is_within_rules(start, end)
            if valid:
                time_diff = abs((start - desired_start).total_seconds() / 60)
                if time_diff < 1:
                    time_reason = "时间完全匹配"
                elif time_diff <= 30:
                    time_reason = f"仅提前{int(time_diff)}分钟"
                elif time_diff <= 60:
                    time_reason = f"提前{int(time_diff)}分钟"
                else:
                    hours = int(time_diff // 60)
                    minutes = int(time_diff % 60)
                    time_reason = f"调整{hours}小时{minutes}分钟"
                slots.append((start, end, base_reasons + [time_reason]))
                return True
        return False
    
    check_and_add_slot(desired_start, desired_end, ["原时间段"])
    
    step = 30
    for i in range(1, max_slots_per_direction + 1):
        offset = timedelta(minutes=step * i)
        if check_and_add_slot(desired_start + offset, desired_end + offset, [f"向后偏移{step * i}分钟"]):
            pass
        if check_and_add_slot(desired_start - offset, desired_end - offset, [f"向前偏移{step * i}分钟"]):
            pass
    
    if not slots:
        for day_offset in range(1, 4):
            for hour_offset in [0, 1, -1, 2, -2]:
                new_start = desired_start + timedelta(days=day_offset, hours=hour_offset)
                new_end = new_start + timedelta(minutes=duration_minutes)
                day_reason = f"延后{day_offset}天"
                if hour_offset != 0:
                    day_reason += f"，时间调整{hour_offset}小时"
                check_and_add_slot(new_start, new_end, [day_reason])
    
    return slots[:max_slots_per_direction * 2]


def calculate_match_score(
    room: models.MeetingRoom,
    start_time: datetime,
    end_time: datetime,
    original_room_id: int,
    original_start: datetime,
    original_end: datetime,
    attendee_count: int,
    required_equipments: List[schemas.BookingEquipmentCreate],
    department_id: Optional[int] = None
) -> Tuple[float, List[str]]:
    score = 100.0
    reasons = []
    
    if room.id == original_room_id:
        reasons.append("原会议室")
    else:
        score -= 10
    
    time_diff = abs((start_time - original_start).total_seconds() / 60)
    if time_diff < 1:
        reasons.append("时间完全匹配")
    elif time_diff <= 30:
        score -= 5
        reasons.append(f"时间相近(差{int(time_diff)}分钟)")
    elif time_diff <= 60:
        score -= 10
        reasons.append(f"时间调整{int(time_diff)}分钟")
    else:
        hours = int(time_diff // 60)
        score -= min(30, hours * 5)
        reasons.append(f"时间调整约{hours}小时")
    
    capacity_diff = room.capacity - attendee_count
    if capacity_diff == 0:
        reasons.append("容量刚好合适")
    elif capacity_diff <= 5:
        score -= 2
        reasons.append(f"容量略有余量(多{capacity_diff}个座位)")
    elif capacity_diff <= 15:
        score -= 5
        reasons.append(f"容量充足(多{capacity_diff}个座位)")
    else:
        score -= 10
        reasons.append(f"容量较大(多{capacity_diff}个座位)")
    
    if required_equipments:
        room_equip_map = {re.equipment_id: re for re in room.equipments}
        matched_count = 0
        for req in required_equipments:
            if req.equipment_id in room_equip_map:
                matched_count += 1
        if matched_count == len(required_equipments):
            reasons.append("设备完全匹配")
        else:
            score -= (len(required_equipments) - matched_count) * 5
            reasons.append(f"匹配{matched_count}/{len(required_equipments)}项设备")
    
    return max(0, score), reasons


def generate_recommendations(
    db: Session,
    original_room_id: int,
    original_start: datetime,
    original_end: datetime,
    attendee_count: int,
    department_id: Optional[int] = None,
    required_equipments: Optional[List[schemas.BookingEquipmentCreate]] = None,
    exclude_booking_id: Optional[int] = None,
    max_recommendations: int = 5,
    title_keywords: Optional[str] = None
) -> schemas.RecommendationResponse:
    if required_equipments is None:
        required_equipments = []
    
    duration_minutes = int((original_end - original_start).total_seconds() / 60)
    
    conflict_reasons = []
    original_room = crud.get_meeting_room(db, original_room_id)
    
    if original_room:
        if attendee_count > original_room.capacity:
            conflict_reasons.append(f"原会议室容量不足(需要{attendee_count}人，仅容纳{original_room.capacity}人)")
        
        if required_equipments:
            equip_ok, equip_issues = check_room_equipment_match(db, original_room, required_equipments)
            if not equip_ok:
                conflict_reasons.extend(equip_issues)
        
        has_conflict, conflicts = crud.check_time_conflict(
            db, original_room_id, original_start, original_end, exclude_booking_id=exclude_booking_id
        )
        if has_conflict:
            conflict_reasons.extend(conflicts)
    
    all_rooms = crud.get_meeting_rooms(db, only_active=True)
    candidates = []
    
    for room in all_rooms:
        if room.capacity < attendee_count:
            continue
        
        equip_ok, _ = check_room_equipment_match(db, room, required_equipments)
        if not equip_ok and room.id != original_room_id:
            continue
        
        time_slots = get_available_time_slots(
            db, room, original_start, original_end, duration_minutes,
            exclude_booking_id=exclude_booking_id, max_slots_per_direction=3
        )
        
        for start, end, time_reasons in time_slots:
            score, score_reasons = calculate_match_score(
                room, start, end, original_room_id, original_start, original_end,
                attendee_count, required_equipments, department_id
            )
            
            all_reasons = list(set(score_reasons + time_reasons))
            
            room_response = schemas.MeetingRoomResponse(
                id=room.id,
                name=room.name,
                capacity=room.capacity,
                location=room.location,
                description=room.description,
                is_active=room.is_active,
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
                    ) for re in room.equipments
                ]
            )
            
            candidates.append(schemas.RecommendationItem(
                room=room_response,
                start_time=start,
                end_time=end,
                match_score=score,
                reasons=all_reasons,
                is_same_room=(room.id == original_room_id),
                is_same_time=(abs((start - original_start).total_seconds()) < 60)
            ))
    
    candidates.sort(key=lambda x: x.match_score, reverse=True)
    top_recommendations = candidates[:max_recommendations]
    
    original_request = {
        "room_id": original_room_id,
        "start_time": original_start.isoformat(),
        "end_time": original_end.isoformat(),
        "attendee_count": attendee_count,
        "department_id": department_id,
        "equipment_count": len(required_equipments)
    }
    
    return schemas.RecommendationResponse(
        original_request=original_request,
        conflict_reasons=conflict_reasons,
        recommendations=top_recommendations,
        total_available=len(candidates)
    )
