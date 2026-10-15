from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import CLINIC_TZ
from .db import Base


def clinic_now() -> datetime:
    """Wall-clock time at the clinic - the same clock the appointment times use."""
    return datetime.now(CLINIC_TZ).replace(tzinfo=None, microsecond=0)

STATUSES = ("BOOKED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW")
ACTIVE_STATUSES = ("BOOKED", "CHECKED_IN")  # these occupy the doctor's calendar

# The front-desk workflow. Anything not listed here is rejected with 409.
TRANSITIONS = {
    "BOOKED": {"CHECKED_IN", "CANCELLED", "NO_SHOW"},
    "CHECKED_IN": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "NO_SHOW": set(),
}


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    specialty: Mapped[str] = mapped_column(String(60))
    room: Mapped[str] = mapped_column(String(20), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clinic_now)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_appointments_time_order"),
        CheckConstraint(f"status IN {STATUSES}", name="ck_appointments_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"), index=True)
    patient_name: Mapped[str] = mapped_column(String(100))
    patient_phone: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # clinic-local time
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="BOOKED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clinic_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=clinic_now, onupdate=clinic_now)

    doctor: Mapped[Doctor] = relationship(back_populates="appointments")
    events: Mapped[list["AppointmentEvent"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan", passive_deletes=True)


class AppointmentEvent(Base):
    """Audit trail: every booking, reschedule and status change is recorded."""

    __tablename__ = "appointment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(20))  # booked | rescheduled | status
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clinic_now, index=True)

    appointment: Mapped[Appointment] = relationship(back_populates="events")
