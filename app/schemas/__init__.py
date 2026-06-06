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


class BookingModifyRequest(BaseModel):
    room_id: Optional[int] = None
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendee_count: Optional[int] = None
    department_id: Optional[int] = None
    equipments: Optional[List[BookingEquipmentCreate]] = None
    change_reason: Optional[str] = None


class BookingCancelRequest(BaseModel):
    cancel_reason: str


class BookingEquipmentChangeResponse(BaseModel):
    id: int
    equipment_id: int
    equipment: EquipmentResponse
    old_quantity: Optional[int] = None
    new_quantity: Optional[int] = None
    change_type: str

    class Config:
        from_attributes = True


class BookingChangeResponse(BaseModel):
    id: int
    booking_id: int
    applicant_id: int
    applicant: Optional[UserResponse] = None
    old_room_id: Optional[int] = None
    new_room_id: Optional[int] = None
    old_room: Optional[MeetingRoomResponse] = None
    new_room: Optional[MeetingRoomResponse] = None
    old_title: Optional[str] = None
    new_title: Optional[str] = None
    old_start_time: Optional[datetime] = None
    new_start_time: Optional[datetime] = None
    old_end_time: Optional[datetime] = None
    new_end_time: Optional[datetime] = None
    old_attendee_count: Optional[int] = None
    new_attendee_count: Optional[int] = None
    old_department_id: Optional[int] = None
    new_department_id: Optional[int] = None
    old_department: Optional[DepartmentResponse] = None
    new_department: Optional[DepartmentResponse] = None
    change_reason: Optional[str] = None
    status: str
    conflict_info: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer: Optional[UserResponse] = None
    review_time: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime
    equipment_changes: List[BookingEquipmentChangeResponse] = []

    class Config:
        from_attributes = True


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
    is_cancelled: bool = False
    cancelled_by_id: Optional[int] = None
    cancelled_by: Optional[UserResponse] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    is_modified: bool = False
    last_modified_at: Optional[datetime] = None
    applicant: Optional[UserResponse] = None
    department: Optional[DepartmentResponse] = None
    room: Optional[MeetingRoomResponse] = None
    equipments: List[BookingEquipmentResponse] = []
    changes: List[BookingChangeResponse] = []

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


class RoomTimeSlot(BaseModel):
    room_id: int
    room_name: str
    start_time: datetime
    end_time: datetime
    capacity: int
    location: Optional[str] = None


class RecommendationItem(BaseModel):
    room: MeetingRoomResponse
    start_time: datetime
    end_time: datetime
    match_score: float
    reasons: List[str]
    is_same_room: bool = False
    is_same_time: bool = False


class RecommendationResponse(BaseModel):
    original_request: dict
    conflict_reasons: List[str]
    recommendations: List[RecommendationItem]
    total_available: int


class ConflictBookingRecord(BaseModel):
    id: int
    type: str
    title: str
    original_room: str
    original_start_time: datetime
    original_end_time: datetime
    attendee_count: int
    department: str
    applicant: str
    status: str
    conflict_info: Optional[str] = None
    recommended_solution: Optional[str] = None
    resolution_status: str
    resolved_at: Optional[datetime] = None
    created_at: datetime


class ConflictBookingStatsResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    total_conflicts: int
    resolved_count: int
    pending_count: int
    resolved_with_conflict: int
    resolved_by_rejection: int
    records: List[ConflictBookingRecord]


class ImportRowResult(BaseModel):
    row_number: int
    success: bool
    booking: Optional[BookingResponse] = None
    errors: List[str] = []
    recommendations: Optional[RecommendationResponse] = None


class ImportResultResponse(BaseModel):
    batch: ImportBatchResponse
    successful_bookings: List[BookingResponse] = []
    failed_rows: List[ImportRowResult] = []


class BookingWithRecommendationResponse(BaseModel):
    booking: Optional[BookingResponse] = None
    success: bool
    errors: List[str] = []
    recommendations: Optional[RecommendationResponse] = None


class BookingChangeWithRecommendationResponse(BaseModel):
    change: Optional[BookingChangeResponse] = None
    success: bool
    errors: List[str] = []
    recommendations: Optional[RecommendationResponse] = None


class OccupancyWithRecommendationResponse(BaseModel):
    occupancy: Optional[TemporaryOccupancyResponse] = None
    success: bool
    errors: List[str] = []
    recommendations: Optional[RecommendationResponse] = None


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
    modified_count: int
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
