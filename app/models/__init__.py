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

    batch = relationship("ImportBatch", back_populates="bookings")
    room = relationship("MeetingRoom", back_populates="bookings")
    applicant = relationship("User", back_populates="bookings", foreign_keys=[applicant_id])
    reviewer = relationship("User", back_populates="reviewed_bookings", foreign_keys=[reviewer_id])
    department = relationship("Department", back_populates="bookings")
    equipments = relationship("BookingEquipment", back_populates="booking", cascade="all, delete-orphan")


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
