from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    department = relationship("Department", back_populates="users")
    bookings = relationship("Booking", back_populates="applicant", foreign_keys="Booking.applicant_id")
    reviewed_bookings = relationship("Booking", back_populates="reviewer", foreign_keys="Booking.reviewer_id")
    created_batches = relationship("ImportBatch", back_populates="created_by")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="department")
    bookings = relationship("Booking", back_populates="department")


class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    location = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    equipments = relationship("RoomEquipment", back_populates="room")
    bookings = relationship("Booking", back_populates="room")
    occupancies = relationship("TemporaryOccupancy", back_populates="room")


class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    room_equipments = relationship("RoomEquipment", back_populates="equipment")
    booking_equipments = relationship("BookingEquipment", back_populates="equipment")


class RoomEquipment(Base):
    __tablename__ = "room_equipments"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    quantity = Column(Integer, default=1)

    room = relationship("MeetingRoom", back_populates="equipments")
    equipment = relationship("Equipment", back_populates="room_equipments")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    title = Column(String(200), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    attendee_count = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")
    conflict_info = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_time = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    is_cancelled = Column(Boolean, default=False)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(Text, nullable=True)
    is_modified = Column(Boolean, default=False)
    last_modified_at = Column(DateTime, nullable=True)

    batch = relationship("ImportBatch", back_populates="bookings")
    room = relationship("MeetingRoom", back_populates="bookings")
    applicant = relationship("User", back_populates="bookings", foreign_keys=[applicant_id])
    reviewer = relationship("User", back_populates="reviewed_bookings", foreign_keys=[reviewer_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    department = relationship("Department", back_populates="bookings")
    equipments = relationship("BookingEquipment", back_populates="booking", cascade="all, delete-orphan")
    changes = relationship("BookingChange", back_populates="booking", cascade="all, delete-orphan")
    reassignments = relationship("BookingReassignment", back_populates="booking", foreign_keys="BookingReassignment.booking_id", cascade="all, delete-orphan")


class BookingChange(Base):
    __tablename__ = "booking_changes"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    old_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=True)
    new_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=True)
    old_title = Column(String(200), nullable=True)
    new_title = Column(String(200), nullable=True)
    old_start_time = Column(DateTime, nullable=True)
    new_start_time = Column(DateTime, nullable=True)
    old_end_time = Column(DateTime, nullable=True)
    new_end_time = Column(DateTime, nullable=True)
    old_attendee_count = Column(Integer, nullable=True)
    new_attendee_count = Column(Integer, nullable=True)
    old_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    new_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    change_reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    conflict_info = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_time = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    booking = relationship("Booking", back_populates="changes")
    applicant = relationship("User", foreign_keys=[applicant_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    old_room = relationship("MeetingRoom", foreign_keys=[old_room_id])
    new_room = relationship("MeetingRoom", foreign_keys=[new_room_id])
    old_department = relationship("Department", foreign_keys=[old_department_id])
    new_department = relationship("Department", foreign_keys=[new_department_id])
    equipment_changes = relationship("BookingEquipmentChange", back_populates="change", cascade="all, delete-orphan")
    reassignments = relationship("BookingReassignment", back_populates="change", foreign_keys="BookingReassignment.change_id", cascade="all, delete-orphan")


class BookingEquipmentChange(Base):
    __tablename__ = "booking_equipment_changes"

    id = Column(Integer, primary_key=True, index=True)
    change_id = Column(Integer, ForeignKey("booking_changes.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    old_quantity = Column(Integer, nullable=True)
    new_quantity = Column(Integer, nullable=True)
    change_type = Column(String(20), nullable=False)

    change = relationship("BookingChange", back_populates="equipment_changes")
    equipment = relationship("Equipment")


class BookingEquipment(Base):
    __tablename__ = "booking_equipments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    quantity = Column(Integer, default=1)

    booking = relationship("Booking", back_populates="equipments")
    equipment = relationship("Equipment", back_populates="booking_equipments")


class TemporaryOccupancy(Base):
    __tablename__ = "temporary_occupancies"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)
    title = Column(String(200), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)

    room = relationship("MeetingRoom", back_populates="occupancies")
    reassignments = relationship("BookingReassignment", back_populates="occupancy", foreign_keys="BookingReassignment.occupancy_id", cascade="all, delete-orphan")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_no = Column(String(50), unique=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String(20), default="processing")
    created_at = Column(DateTime, nullable=False)

    created_by = relationship("User", back_populates="created_batches")
    bookings = relationship("Booking", back_populates="batch")
    errors = relationship("ImportError", back_populates="batch", cascade="all, delete-orphan")


class ImportError(Base):
    __tablename__ = "import_errors"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    error_type = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    row_data = Column(Text, nullable=True)

    batch = relationship("ImportBatch", back_populates="errors")


class BookingReassignment(Base):
    __tablename__ = "booking_reassignments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    change_id = Column(Integer, ForeignKey("booking_changes.id"), nullable=True)
    occupancy_id = Column(Integer, ForeignKey("temporary_occupancies.id"), nullable=True)
    source_type = Column(String(30), nullable=False)
    original_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)
    original_start_time = Column(DateTime, nullable=False)
    original_end_time = Column(DateTime, nullable=False)
    original_attendee_count = Column(Integer, nullable=True)
    reassigned_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)
    reassigned_start_time = Column(DateTime, nullable=False)
    reassigned_end_time = Column(DateTime, nullable=False)
    reassigned_attendee_count = Column(Integer, nullable=True)
    conflict_reasons = Column(Text, nullable=True)
    recommendation_index = Column(Integer, nullable=True)
    match_score = Column(Float, nullable=True)
    recommendation_reasons = Column(Text, nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operated_at = Column(DateTime, nullable=False)
    processing_note = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_time = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)

    booking = relationship("Booking", foreign_keys=[booking_id])
    change = relationship("BookingChange", foreign_keys=[change_id])
    occupancy = relationship("TemporaryOccupancy", foreign_keys=[occupancy_id])
    original_room = relationship("MeetingRoom", foreign_keys=[original_room_id])
    reassigned_room = relationship("MeetingRoom", foreign_keys=[reassigned_room_id])
    operator = relationship("User", foreign_keys=[operator_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    equipment_diffs = relationship("ReassignmentEquipmentDiff", back_populates="reassignment", cascade="all, delete-orphan")


class ReassignmentEquipmentDiff(Base):
    __tablename__ = "reassignment_equipment_diffs"

    id = Column(Integer, primary_key=True, index=True)
    reassignment_id = Column(Integer, ForeignKey("booking_reassignments.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    old_quantity = Column(Integer, nullable=True)
    new_quantity = Column(Integer, nullable=True)
    diff_type = Column(String(20), nullable=False)

    reassignment = relationship("BookingReassignment", back_populates="equipment_diffs")
    equipment = relationship("Equipment")


class BookingRule(Base):
    __tablename__ = "booking_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), unique=True, nullable=False)
    max_booking_days = Column(Integer, default=30)
    min_booking_hours = Column(Integer, default=0)
    max_booking_hours = Column(Integer, default=8)
    require_approval = Column(Boolean, default=True)
    allow_weekend = Column(Boolean, default=False)
    start_time_limit = Column(String(10), default="08:00")
    end_time_limit = Column(String(10), default="20:00")
    max_attendees_per_room = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
