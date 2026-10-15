"""ClinicFlow - front-desk appointment booking API for a multi-doctor clinic."""
import logging
import socket
from datetime import date, datetime, time, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as http_metrics
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from . import metrics
from .config import (APP_ENV, APP_VERSION, CLINIC_TZ, CLOSING_HOUR, CORS_ORIGINS, OPENING_HOUR,
                     SLOT_MINUTES)
from .db import SessionLocal, get_db
from .models import (ACTIVE_STATUSES, STATUSES, TRANSITIONS, Appointment, AppointmentEvent, Doctor,
                     clinic_now)
from .schemas import (AppointmentIn, AppointmentOut, AppointmentUpdate, DoctorDay, DoctorIn, DoctorOut,
                      EventOut, Info, Slot, Stats, StatusChange)

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("clinicflow")


class QuietProbes(logging.Filter):
    """Keep kubelet probes and Prometheus scrapes (every few seconds per pod) out of the access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args if isinstance(record.args, tuple) else ()
        return not (len(args) >= 3 and str(args[2]).startswith(("/health", "/ready", "/metrics")))


logging.getLogger("uvicorn.access").addFilter(QuietProbes())

app = FastAPI(title="ClinicFlow API", version=APP_VERSION,
              description="Clinic front desk: doctors, appointment booking without double-booking, "
                          "a check-in workflow with an audit trail, and daily KPIs.")
if CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

# Request count + latency per route. The default latency buckets start at 100 ms; this API
# answers in a few ms, so p95 would be a meaningless interpolation inside the first bucket.
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).add(
    http_metrics.default(latency_lowr_buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
metrics.register(SessionLocal)


# --- helpers -------------------------------------------------------------------------------------

def _local(dt: datetime) -> datetime:
    """Store clinic wall-clock time. A timestamp with an offset is converted to the clinic's zone."""
    return dt.astimezone(CLINIC_TZ).replace(tzinfo=None) if dt.tzinfo else dt


def _day(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time())
    return start, start + timedelta(days=1)


def _out(a: Appointment) -> AppointmentOut:
    return AppointmentOut(id=a.id, doctor_id=a.doctor_id, doctor_name=a.doctor.name, patient_name=a.patient_name,
                          patient_phone=a.patient_phone, reason=a.reason, starts_at=a.starts_at, ends_at=a.ends_at,
                          status=a.status)


def _doctor_or_404(db: Session, doctor_id: int, lock: bool = False) -> Doctor:
    stmt = select(Doctor).where(Doctor.id == doctor_id)
    if lock:
        # Serialise bookings per doctor: two replicas booking the same doctor at the same moment
        # queue here, so the overlap check below can never miss the other's insert.
        stmt = stmt.with_for_update()
    doctor = db.scalars(stmt).first()
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"doctor {doctor_id} not found")
    return doctor


def _appointment_or_404(db: Session, appointment_id: int) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"appointment {appointment_id} not found")
    return appt


def _check_slot(db: Session, doctor_id: int, start: datetime, end: datetime, exclude_id: int | None = None) -> Doctor:
    doctor = _doctor_or_404(db, doctor_id, lock=True)
    if not doctor.active:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{doctor.name} is not taking appointments")
    opens, closes = datetime.combine(start.date(), time(OPENING_HOUR)), datetime.combine(start.date(), time(CLOSING_HOUR))
    if start < opens or end > closes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"outside opening hours ({OPENING_HOUR:02d}:00-{CLOSING_HOUR:02d}:00)")
    stmt = select(Appointment).where(Appointment.doctor_id == doctor_id, Appointment.status.in_(ACTIVE_STATUSES),
                                     Appointment.starts_at < end, Appointment.ends_at > start)
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    clash = db.scalars(stmt.limit(1)).first()
    if clash:
        metrics.BOOKING_CONFLICTS.inc()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"{doctor.name} is already booked {clash.starts_at:%H:%M}-{clash.ends_at:%H:%M}")
    return doctor


# --- ops -------------------------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return {"service": "clinicflow-api", "env": APP_ENV, "version": APP_VERSION, "docs": "/docs"}


@app.get("/health", tags=["ops"])
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: the database is reachable AND the schema has been migrated."""
    try:
        db.execute(text("SELECT 1 FROM appointment_events LIMIT 1"))
    except Exception as exc:  # noqa: BLE001 - any DB failure means "not ready"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "reason": type(exc).__name__}
    return {"status": "ready", "version": APP_VERSION}


@app.get("/api/info", response_model=Info, tags=["ops"])
def info():
    """Which build is answering, and from which pod (used by the smoke test and the GitOps demo)."""
    return Info(service="clinicflow-api", version=APP_VERSION, environment=APP_ENV, pod=socket.gethostname())


# --- doctors ---------------------------------------------------------------------------------------

@app.get("/api/doctors", response_model=list[DoctorOut], tags=["doctors"])
def list_doctors(active: bool | None = None, db: Session = Depends(get_db)):
    stmt = select(Doctor).order_by(Doctor.name)
    if active is not None:
        stmt = stmt.where(Doctor.active == active)
    return db.scalars(stmt).all()


@app.post("/api/doctors", response_model=DoctorOut, status_code=status.HTTP_201_CREATED, tags=["doctors"])
def create_doctor(body: DoctorIn, db: Session = Depends(get_db)):
    doctor = Doctor(**body.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@app.put("/api/doctors/{doctor_id}", response_model=DoctorOut, tags=["doctors"])
def update_doctor(doctor_id: int, body: DoctorIn, db: Session = Depends(get_db)):
    doctor = _doctor_or_404(db, doctor_id)
    for field, value in body.model_dump().items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return doctor


@app.delete("/api/doctors/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["doctors"])
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = _doctor_or_404(db, doctor_id)
    if db.scalar(select(func.count()).where(Appointment.doctor_id == doctor_id)):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"{doctor.name} has appointment history - set active=false instead of deleting")
    db.delete(doctor)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/doctors/{doctor_id}/slots", response_model=list[Slot], tags=["doctors"])
def free_slots(doctor_id: int, day: date = Query(alias="date"), db: Session = Depends(get_db)):
    """The doctor's calendar for one day in SLOT_MINUTES steps; past slots are never available."""
    _doctor_or_404(db, doctor_id)
    busy = db.execute(select(Appointment.starts_at, Appointment.ends_at).where(
        Appointment.doctor_id == doctor_id, Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.starts_at >= _day(day)[0], Appointment.starts_at < _day(day)[1])).all()
    now, step = clinic_now(), timedelta(minutes=SLOT_MINUTES)
    slot, closes, out = datetime.combine(day, time(OPENING_HOUR)), datetime.combine(day, time(CLOSING_HOUR)), []
    while slot + step <= closes:
        taken = any(s < slot + step and e > slot for s, e in busy)
        out.append(Slot(starts_at=slot, available=not taken and slot > now))
        slot += step
    return out


# --- appointments ----------------------------------------------------------------------------------

@app.get("/api/appointments", response_model=list[AppointmentOut], tags=["appointments"])
def list_appointments(day: date | None = Query(None, alias="date"), doctor_id: int | None = None,
                      appt_status: str | None = Query(None, alias="status"),
                      q: str | None = Query(None, max_length=60), db: Session = Depends(get_db)):
    stmt = select(Appointment).join(Doctor).order_by(Appointment.starts_at, Doctor.name)
    if day:
        start, end = _day(day)
        stmt = stmt.where(Appointment.starts_at >= start, Appointment.starts_at < end)
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if appt_status:
        stmt = stmt.where(Appointment.status == appt_status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Appointment.patient_name.ilike(like), Appointment.patient_phone.ilike(like)))
    return [_out(a) for a in db.scalars(stmt)]


@app.get("/api/appointments/{appointment_id}", response_model=AppointmentOut, tags=["appointments"])
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    return _out(_appointment_or_404(db, appointment_id))


@app.post("/api/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED,
          tags=["appointments"])
def book_appointment(body: AppointmentIn, db: Session = Depends(get_db)):
    start = _local(body.starts_at)
    end = start + timedelta(minutes=body.duration_min)
    doctor = _check_slot(db, body.doctor_id, start, end)
    appt = Appointment(doctor_id=doctor.id, patient_name=body.patient_name, patient_phone=body.patient_phone,
                       reason=body.reason, starts_at=start, ends_at=end, status="BOOKED")
    db.add(appt)
    db.flush()
    db.add(AppointmentEvent(appointment_id=appt.id, action="booked", to_status="BOOKED",
                            note=f"{doctor.name}, {start:%d %b %H:%M}"))
    db.commit()
    db.refresh(appt)  # return what the database stored, not an echo of the request
    log.info("appointment booked id=%s doctor=%s", appt.id, doctor.id)
    return _out(appt)


@app.put("/api/appointments/{appointment_id}", response_model=AppointmentOut, tags=["appointments"])
def reschedule_appointment(appointment_id: int, body: AppointmentUpdate, db: Session = Depends(get_db)):
    appt = _appointment_or_404(db, appointment_id)
    if appt.status != "BOOKED":
        raise HTTPException(status.HTTP_409_CONFLICT, f"only BOOKED appointments can be changed (this one is {appt.status})")
    start = _local(body.starts_at)
    end = start + timedelta(minutes=body.duration_min)
    doctor = _check_slot(db, body.doctor_id, start, end, exclude_id=appt.id)
    moved = (appt.doctor_id, appt.starts_at) != (doctor.id, start)
    appt.doctor_id, appt.starts_at, appt.ends_at = doctor.id, start, end
    appt.patient_name, appt.patient_phone, appt.reason = body.patient_name, body.patient_phone, body.reason
    db.add(AppointmentEvent(appointment_id=appt.id, action="rescheduled" if moved else "updated",
                            note=f"{doctor.name}, {start:%d %b %H:%M}" if moved else "details corrected"))
    db.commit()
    db.refresh(appt)
    return _out(appt)


@app.delete("/api/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["appointments"])
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Remove a booking made in error. A real cancellation should use /status so it stays on record."""
    db.delete(_appointment_or_404(db, appointment_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/appointments/{appointment_id}/status", response_model=AppointmentOut, tags=["workflow"])
def change_status(appointment_id: int, body: StatusChange, db: Session = Depends(get_db)):
    """Front-desk workflow: BOOKED -> CHECKED_IN -> COMPLETED, or CANCELLED / NO_SHOW. Every change is audited."""
    appt = db.scalars(select(Appointment).where(Appointment.id == appointment_id).with_for_update()).first()
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"appointment {appointment_id} not found")
    if body.status not in TRANSITIONS[appt.status]:
        allowed = ", ".join(sorted(TRANSITIONS[appt.status])) or "none - it is final"
        raise HTTPException(status.HTTP_409_CONFLICT, f"cannot go from {appt.status} to {body.status} (allowed: {allowed})")
    db.add(AppointmentEvent(appointment_id=appt.id, action="status", from_status=appt.status,
                            to_status=body.status, note=body.note))
    appt.status = body.status
    db.commit()
    db.refresh(appt)
    metrics.STATUS_CHANGES.labels(status=body.status).inc()
    return _out(appt)


@app.get("/api/events", response_model=list[EventOut], tags=["workflow"])
def list_events(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.execute(
        select(AppointmentEvent, Appointment.patient_name, Doctor.name)
        .join(Appointment, AppointmentEvent.appointment_id == Appointment.id).join(Doctor)
        .order_by(AppointmentEvent.created_at.desc(), AppointmentEvent.id.desc()).limit(limit)).all()
    return [EventOut(id=e.id, appointment_id=e.appointment_id, patient_name=p, doctor_name=d, action=e.action,
                     from_status=e.from_status, to_status=e.to_status, note=e.note, created_at=e.created_at)
            for e, p, d in rows]


@app.get("/api/stats", response_model=Stats, tags=["workflow"])
def stats(day: date | None = Query(None, alias="date"), db: Session = Depends(get_db)):
    day = day or clinic_now().date()
    start, end = _day(day)
    rows = db.execute(select(Appointment.doctor_id, Appointment.status, Appointment.starts_at, Appointment.ends_at)
                      .where(Appointment.starts_at >= start, Appointment.starts_at < end)).all()
    by_status = dict.fromkeys(STATUSES, 0)
    for r in rows:
        by_status[r.status] += 1
    open_minutes = (CLOSING_HOUR - OPENING_HOUR) * 60
    doctors = []
    for doc in db.scalars(select(Doctor).where(Doctor.active).order_by(Doctor.name)):
        mine = [r for r in rows if r.doctor_id == doc.id and r.status != "CANCELLED"]
        minutes = sum((r.ends_at - r.starts_at).total_seconds() / 60 for r in mine)
        doctors.append(DoctorDay(doctor_id=doc.id, doctor_name=doc.name, booked=len(mine),
                                 completed=sum(r.status == "COMPLETED" for r in mine),
                                 utilization=round(minutes / open_minutes, 3)))
    return Stats(date=day, total_today=len(rows), by_status=by_status, waiting_now=by_status["CHECKED_IN"],
                 no_show_rate_30d=metrics.no_show_rate(db, clinic_now()), doctors=doctors)
