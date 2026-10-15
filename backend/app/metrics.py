"""Business metrics for Prometheus.

Gauges are computed from the database at scrape time (not updated on write), so every replica
reports the same, correct numbers - including a pod that has just started. Counters count events
handled by this pod; Prometheus sums them across pods.
"""
import logging
from datetime import datetime, time, timedelta

from prometheus_client import Counter
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from sqlalchemy import func, select

log = logging.getLogger("clinicflow.metrics")

BOOKING_CONFLICTS = Counter("clinic_booking_conflicts_total",
                            "Bookings rejected because the doctor was already booked")
STATUS_CHANGES = Counter("clinic_status_changes_total", "Appointment status changes", ["status"])


def no_show_rate(db, now: datetime) -> float:
    """Share of finished appointments in the last 30 days where the patient did not come."""
    from .models import Appointment

    rows = dict(db.execute(select(Appointment.status, func.count()).where(
        Appointment.starts_at >= now - timedelta(days=30), Appointment.starts_at <= now,
        Appointment.status.in_(("COMPLETED", "NO_SHOW"))).group_by(Appointment.status)).all())
    finished = rows.get("COMPLETED", 0) + rows.get("NO_SHOW", 0)
    return round(rows.get("NO_SHOW", 0) / finished, 3) if finished else 0.0


class ClinicCollector:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def collect(self):
        from .config import CLINIC_TZ
        from .models import STATUSES, Appointment, Doctor  # local import avoids a cycle at load

        today = GaugeMetricFamily("clinic_appointments_today", "Appointments scheduled today, by status",
                                  labels=["status"])
        waiting = GaugeMetricFamily("clinic_patients_waiting", "Patients checked in and waiting to be seen")
        noshow = GaugeMetricFamily("clinic_no_show_ratio_30d", "No-shows / finished appointments, last 30 days")
        doctors = GaugeMetricFamily("clinic_doctors_active", "Doctors taking appointments")
        now = datetime.now(CLINIC_TZ).replace(tzinfo=None)
        start = datetime.combine(now.date(), time())
        try:
            with self._session_factory() as db:
                counts = dict(db.execute(select(Appointment.status, func.count()).where(
                    Appointment.starts_at >= start, Appointment.starts_at < start + timedelta(days=1))
                    .group_by(Appointment.status)).all())
                ratio = no_show_rate(db, now)
                active = db.scalar(select(func.count()).where(Doctor.active)) or 0
        except Exception:  # noqa: BLE001 - a DB outage must not break the whole /metrics scrape
            log.warning("clinic metrics unavailable: database not reachable")
            return
        for s in STATUSES:
            today.add_metric([s], counts.get(s, 0))
        waiting.add_metric([], counts.get("CHECKED_IN", 0))
        noshow.add_metric([], ratio)
        doctors.add_metric([], active)
        yield from (today, waiting, noshow, doctors)


_registered = False


def register(session_factory):
    global _registered
    if not _registered:
        REGISTRY.register(ClinicCollector(session_factory))
        _registered = True
