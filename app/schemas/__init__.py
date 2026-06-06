from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    full_name: str
    role: str
    department_id: Optional[int] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        from_attributes = True


class EquipmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class EquipmentResponse(EquipmentBase):
    id: int

    class Config:
        from_attributes = True


class RoomEquipmentBase(BaseModel):
    equipment_id: int
    quantity: int = 1


class RoomEquipmentCreate(RoomEquipmentBase):
    pass


class RoomEquipmentResponse(RoomEquipmentBase):
    id: int
    equipment: EquipmentResponse

    class Config:
        from_attributes = True


class MeetingRoomBase(BaseModel):
    name: str
    capacity: int
    location: Optional[str] = None
    description: Optional[str] = None


class MeetingRoomCreate(MeetingRoomBase):
    equipments: List[RoomEquipmentCreate] = []


class MeetingRoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    equipments: Optional[List[RoomEquipmentCreate]] = None


class MeetingRoomResponse(MeetingRoomBase):
    id: int
    is_active: bool
    equipments: List[RoomEquipmentResponse] = []

    class Config:
        from_attributes = True


class BookingEquipmentBase(BaseModel):
    equipment_id: int
    quantity: int = 1


class BookingEquipmentCreate(BookingEquipmentBase):
    pass


class BookingEquipmentResponse(BookingEquipmentBase):
    id: int
    equipment: EquipmentResponse

    class Config:
        from_attributes = True


class BookingBase(BaseModel):
    room_id: int
    title: str
    start_time: datetime
    end_time: datetime
    attendee_count: int
    department_id: int
    equipments: List[BookingEquipmentCreate] = []


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    review_comment: Optional[str] = None


class BookingResponse(BookingBase):
    id: int
    status: str
    conflict_info: Optional[str] = None
    applicant_id: int
    reviewer_id: Optional[int] = None
    review_time: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime
    batch_id: Optional[int] = None
    applicant: Optional[UserResponse] = None
    department: Optional[DepartmentResponse] = None
    room: Optional[MeetingRoomResponse] = None
    equipments: List[BookingEquipmentResponse] = []

    class Config:
        from_attributes = True


class TemporaryOccupancyBase(BaseModel):
    room_id: int
    title: str
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None


class TemporaryOccupancyCreate(TemporaryOccupancyBase):
    pass


class TemporaryOccupancyResponse(TemporaryOccupancyBase):
    id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ImportErrorResponse(BaseModel):
    id: int
    row_number: int
    error_type: str
    error_message: str
    row_data: Optional[str] = None

    class Config:
        from_attributes = True


class ImportBatchBase(BaseModel):
    pass


class ImportBatchResponse(ImportBatchBase):
    id: int
    batch_no: str
    file_name: str
    total_count: int
    success_count: int
    error_count: int
    status: str
    created_at: datetime
    created_by: Optional[UserResponse] = None
    errors: List[ImportErrorResponse] = []

    class Config:
        from_attributes = True


class ImportResultResponse(BaseModel):
    batch: ImportBatchResponse
    successful_bookings: List[BookingResponse] = []


class BookingQueryParams(BaseModel):
    room_id: Optional[int] = None
    department_id: Optional[int] = None
    applicant_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class OccupancyStatsResponse(BaseModel):
    room_id: int
    room_name: str
    total_bookings: int
    total_occupancy_hours: float
    pending_count: int
    approved_count: int
    rejected_count: int
    occupancy_rate: float


class BookingRuleBase(BaseModel):
    rule_name: str
    max_booking_days: int = 30
    min_booking_hours: int = 0
    max_booking_hours: int = 8
    require_approval: bool = True
    allow_weekend: bool = False
    start_time_limit: str = "08:00"
    end_time_limit: str = "20:00"
    max_attendees_per_room: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True


class BookingRuleCreate(BookingRuleBase):
    pass


class BookingRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    max_booking_days: Optional[int] = None
    min_booking_hours: Optional[int] = None
    max_booking_hours: Optional[int] = None
    require_approval: Optional[bool] = None
    allow_weekend: Optional[bool] = None
    start_time_limit: Optional[str] = None
    end_time_limit: Optional[str] = None
    max_attendees_per_room: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BookingRuleResponse(BookingRuleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
