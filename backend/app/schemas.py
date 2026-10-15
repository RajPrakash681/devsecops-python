from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["BOOKED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"]
Phone = Field(pattern=r"^\+?[0-9][0-9 -]{6,18}$")


class DoctorIn(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    specialty: str = Field(min_length=2, max_length=60)
    room: str = Field("", max_length=20)
    active: bool = True


class DoctorOut(DoctorIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AppointmentIn(BaseModel):
    doctor_id: int
    patient_name: str = Field(min_length=2, max_length=100)
    patient_phone: str = Phone
    reason: str = Field("", max_length=500)
    starts_at: datetime
    duration_min: int = Field(30, ge=10, le=120)


class AppointmentUpdate(BaseModel):
    """PUT = reschedule / correct details. Status changes go through /status so they are audited."""

    doctor_id: int
    patient_name: str = Field(min_length=2, max_length=100)
    patient_phone: str = Phone
    reason: str = Field("", max_length=500)
    starts_at: datetime
    duration_min: int = Field(30, ge=10, le=120)


class StatusChange(BaseModel):
    status: Status
    note: str = Field("", max_length=200)


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    doctor_name: str
    patient_name: str
    patient_phone: str
    reason: str
    starts_at: datetime
    ends_at: datetime
    status: Status


class EventOut(BaseModel):
    id: int
    appointment_id: int
    patient_name: str
    doctor_name: str
    action: str
    from_status: str | None
    to_status: str | None
    note: str
    created_at: datetime


class Slot(BaseModel):
    starts_at: datetime
    available: bool


class DoctorDay(BaseModel):
    doctor_id: int
    doctor_name: str
    booked: int
    completed: int
    utilization: float  # booked minutes / opening-hours minutes


class Stats(BaseModel):
    date: date
    total_today: int
    by_status: dict[str, int]
    waiting_now: int
    no_show_rate_30d: float
    doctors: list[DoctorDay]


class Info(BaseModel):
    service: str
    version: str
    environment: str
    pod: str
    opening_hour: int
    closing_hour: int
    slot_minutes: int
