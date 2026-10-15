from datetime import date, timedelta

import pytest

from app.models import clinic_now

TOMORROW = (clinic_now().date() + timedelta(days=1)).isoformat()
YESTERDAY = (clinic_now().date() - timedelta(days=1)).isoformat()


def at(hhmm, day=TOMORROW):
    return f"{day}T{hhmm}:00"


# --- ops endpoints -----------------------------------------------------------------------------

def test_health_does_not_need_the_database(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_ready_when_schema_is_migrated(client):
    r = client.get("/ready")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def test_info_reports_build_and_pod(client):
    body = client.get("/api/info").json()
    assert body["service"] == "clinicflow-api" and body["pod"]


# --- doctors -----------------------------------------------------------------------------------

def test_create_list_and_filter_doctors(client, make_doctor):
    make_doctor("Dr. Meera Iyer")
    make_doctor("Dr. Kabir Rao", specialty="Paediatrics", active=False)
    assert [d["name"] for d in client.get("/api/doctors").json()] == ["Dr. Kabir Rao", "Dr. Meera Iyer"]
    assert [d["name"] for d in client.get("/api/doctors?active=true").json()] == ["Dr. Meera Iyer"]


def test_update_doctor_and_404(client, make_doctor):
    doc = make_doctor()
    r = client.put(f"/api/doctors/{doc['id']}", json={**doc, "room": "204", "active": False})
    assert r.status_code == 200 and r.json()["room"] == "204" and r.json()["active"] is False
    assert client.put("/api/doctors/999", json={**doc}).status_code == 404


def test_delete_doctor_only_without_history(client, make_doctor, book):
    free, busy = make_doctor("Dr. New Joiner"), make_doctor()
    book(busy["id"], at("10:00"))
    assert client.delete(f"/api/doctors/{free['id']}").status_code == 204
    r = client.delete(f"/api/doctors/{busy['id']}")
    assert r.status_code == 409 and "active=false" in r.json()["detail"]


@pytest.mark.parametrize("payload", [{"name": "Dr", "specialty": "GP"}, {"name": "Dr. Valid", "specialty": "G"}])
def test_doctor_validation(client, payload):
    assert client.post("/api/doctors", json=payload).status_code == 422


# --- booking -----------------------------------------------------------------------------------

def test_book_returns_stored_row_and_records_event(client, make_doctor, book):
    doc = make_doctor()
    appt = book(doc["id"], at("10:00"), duration_min=45)
    assert appt["status"] == "BOOKED" and appt["doctor_name"] == "Dr. Meera Iyer"
    assert appt["starts_at"] == at("10:00") and appt["ends_at"] == at("10:45")
    event = client.get("/api/events").json()[0]
    assert (event["appointment_id"], event["action"], event["to_status"]) == (appt["id"], "booked", "BOOKED")


def test_double_booking_is_rejected(client, make_doctor, book):
    doc = make_doctor()
    book(doc["id"], at("10:00"), duration_min=30)
    r = client.post("/api/appointments", json={"doctor_id": doc["id"], "patient_name": "Second Patient",
                                               "patient_phone": "9876543210", "starts_at": at("10:15")})
    assert r.status_code == 409 and "already booked 10:00-10:30" in r.json()["detail"]


def test_back_to_back_and_other_doctor_are_fine(make_doctor, book):
    a, b = make_doctor(), make_doctor("Dr. Kabir Rao")
    book(a["id"], at("10:00"))
    book(a["id"], at("10:30"))          # starts exactly when the previous one ends
    book(b["id"], at("10:00"))          # same time, different doctor


def test_cancelled_slot_can_be_rebooked(client, make_doctor, book):
    doc = make_doctor()
    first = book(doc["id"], at("11:00"))
    client.post(f"/api/appointments/{first['id']}/status", json={"status": "CANCELLED"})
    book(doc["id"], at("11:00"), patient_name="Walk In")


def test_outside_opening_hours_and_inactive_or_unknown_doctor(make_doctor, book):
    doc = make_doctor()
    book(doc["id"], at("08:30"), expect=422)
    book(doc["id"], at("17:45"), expect=422)          # would end 18:15, after closing
    off = make_doctor("Dr. On Leave", active=False)
    book(off["id"], at("10:00"), expect=409)
    book(9999, at("10:00"), expect=404)


@pytest.mark.parametrize("bad", [
    {"patient_name": "A"},                  # too short
    {"patient_phone": "call me"},           # not a phone number
    {"duration_min": 5},                    # shorter than 10 minutes
    {"starts_at": "tomorrow morning"},      # not a timestamp
])
def test_booking_validation(make_doctor, book, bad):
    book(make_doctor()["id"], **{"starts_at": at("10:00"), **bad}, expect=422)


def test_timezone_aware_input_is_stored_in_clinic_time(make_doctor, book):
    appt = book(make_doctor()["id"], f"{TOMORROW}T04:30:00Z")   # 04:30 UTC = 10:00 in Asia/Kolkata
    assert appt["starts_at"] == at("10:00")


def test_list_filters_and_get(client, make_doctor, book):
    a, b = make_doctor(), make_doctor("Dr. Kabir Rao")
    first = book(a["id"], at("09:00"), patient_name="Arjun Mehta")
    book(b["id"], at("09:30"), patient_name="Sara Khan")
    book(a["id"], at("10:00", YESTERDAY), patient_name="Old Visit")
    assert [x["patient_name"] for x in client.get(f"/api/appointments?date={TOMORROW}").json()] == ["Arjun Mehta", "Sara Khan"]
    assert [x["patient_name"] for x in client.get(f"/api/appointments?doctor_id={b['id']}").json()] == ["Sara Khan"]
    assert [x["patient_name"] for x in client.get("/api/appointments?q=sara").json()] == ["Sara Khan"]
    assert client.get(f"/api/appointments/{first['id']}").json()["patient_name"] == "Arjun Mehta"
    assert client.get("/api/appointments/4242").status_code == 404


def test_free_slots(client, make_doctor, book):
    doc = make_doctor()
    book(doc["id"], at("10:00"), duration_min=60)
    slots = {s["starts_at"][11:16]: s["available"] for s in client.get(f"/api/doctors/{doc['id']}/slots?date={TOMORROW}").json()}
    assert len(slots) == 18 and slots["09:30"] and not slots["10:00"] and not slots["10:30"] and slots["11:00"]
    past = client.get(f"/api/doctors/{doc['id']}/slots?date={YESTERDAY}").json()
    assert not any(s["available"] for s in past)


# --- reschedule / delete -----------------------------------------------------------------------

def test_reschedule(client, make_doctor, book):
    doc = make_doctor()
    appt = book(doc["id"], at("10:00"))
    book(doc["id"], at("12:00"), patient_name="Blocker")
    body = {"doctor_id": doc["id"], "patient_name": "Arjun Mehta", "patient_phone": "+91 98765 43210",
            "starts_at": at("11:00"), "duration_min": 30}
    r = client.put(f"/api/appointments/{appt['id']}", json=body)
    assert r.status_code == 200 and r.json()["starts_at"] == at("11:00")
    assert client.get("/api/events").json()[0]["action"] == "rescheduled"
    assert client.put(f"/api/appointments/{appt['id']}", json={**body, "starts_at": at("12:00")}).status_code == 409
    assert client.put(f"/api/appointments/{appt['id']}", json={**body, "starts_at": at("11:00")}).status_code == 200


def test_cannot_reschedule_after_check_in(client, make_doctor, book):
    doc = make_doctor()
    appt = book(doc["id"], at("10:00"))
    client.post(f"/api/appointments/{appt['id']}/status", json={"status": "CHECKED_IN"})
    body = {"doctor_id": doc["id"], "patient_name": "X Y", "patient_phone": "9876543210", "starts_at": at("15:00")}
    assert client.put(f"/api/appointments/{appt['id']}", json=body).status_code == 409


def test_delete_appointment_cascades_events(client, make_doctor, book):
    appt = book(make_doctor()["id"], at("10:00"))
    assert client.delete(f"/api/appointments/{appt['id']}").status_code == 204
    assert client.get("/api/events").json() == []
    assert client.delete(f"/api/appointments/{appt['id']}").status_code == 404


# --- workflow ----------------------------------------------------------------------------------

def test_check_in_then_complete_is_audited(client, make_doctor, book):
    appt = book(make_doctor()["id"], at("10:00"))
    r = client.post(f"/api/appointments/{appt['id']}/status", json={"status": "CHECKED_IN", "note": "arrived 09:55"})
    assert r.status_code == 200 and r.json()["status"] == "CHECKED_IN"
    assert client.post(f"/api/appointments/{appt['id']}/status", json={"status": "COMPLETED"}).json()["status"] == "COMPLETED"
    events = client.get("/api/events?limit=2").json()
    assert [(e["from_status"], e["to_status"]) for e in events] == [("CHECKED_IN", "COMPLETED"), ("BOOKED", "CHECKED_IN")]
    assert events[1]["note"] == "arrived 09:55"


@pytest.mark.parametrize("path,target", [
    ([], "COMPLETED"),                      # cannot complete without checking in
    (["NO_SHOW"], "CHECKED_IN"),            # NO_SHOW is final
    (["CHECKED_IN", "COMPLETED"], "CANCELLED"),
])
def test_illegal_transitions_are_409(client, make_doctor, book, path, target):
    appt = book(make_doctor()["id"], at("10:00"))
    for step in path:
        client.post(f"/api/appointments/{appt['id']}/status", json={"status": step})
    r = client.post(f"/api/appointments/{appt['id']}/status", json={"status": target})
    assert r.status_code == 409 and "cannot go from" in r.json()["detail"]


def test_status_validation_and_events_limit(client, make_doctor, book):
    appt = book(make_doctor()["id"], at("10:00"))
    assert client.post(f"/api/appointments/{appt['id']}/status", json={"status": "LOST"}).status_code == 422
    assert client.post("/api/appointments/999/status", json={"status": "CANCELLED"}).status_code == 404
    assert client.get("/api/events?limit=0").status_code == 422


# --- stats and metrics -------------------------------------------------------------------------

def test_stats_for_a_day(client, make_doctor, book):
    a, b = make_doctor(), make_doctor("Dr. Kabir Rao")
    x = book(a["id"], at("09:00"), duration_min=60)
    book(a["id"], at("10:00"))
    y = book(b["id"], at("09:00"))
    client.post(f"/api/appointments/{x['id']}/status", json={"status": "CHECKED_IN"})
    client.post(f"/api/appointments/{y['id']}/status", json={"status": "CANCELLED"})
    s = client.get(f"/api/stats?date={TOMORROW}").json()
    assert s["total_today"] == 3 and s["waiting_now"] == 1
    assert s["by_status"] == {"BOOKED": 1, "CHECKED_IN": 1, "COMPLETED": 0, "CANCELLED": 1, "NO_SHOW": 0}
    per_doc = {d["doctor_name"]: (d["booked"], d["utilization"]) for d in s["doctors"]}
    assert per_doc == {"Dr. Meera Iyer": (2, round(90 / 540, 3)), "Dr. Kabir Rao": (0, 0.0)}


def test_no_show_rate_over_last_30_days(client, make_doctor, book):
    doc = make_doctor()
    came, missed = book(doc["id"], at("10:00", YESTERDAY)), book(doc["id"], at("11:00", YESTERDAY))
    for appt, path in ((came, ["CHECKED_IN", "COMPLETED"]), (missed, ["NO_SHOW"])):
        for step in path:
            client.post(f"/api/appointments/{appt['id']}/status", json={"status": step})
    assert client.get("/api/stats").json()["no_show_rate_30d"] == 0.5


def test_metrics_expose_http_and_business_series(client, make_doctor, book):
    doc = make_doctor()
    today = clinic_now().date().isoformat()
    appt = book(doc["id"], at("09:00", today))
    client.post(f"/api/appointments/{appt['id']}/status", json={"status": "CHECKED_IN"})
    book(doc["id"], at("09:00", today), expect=409)                 # one rejected double booking
    body = client.get("/metrics").text
    assert 'clinic_appointments_today{status="CHECKED_IN"} 1.0' in body
    assert "clinic_patients_waiting 1.0" in body
    assert "clinic_doctors_active 1.0" in body
    assert 'clinic_status_changes_total{status="CHECKED_IN"}' in body
    conflicts = [line for line in body.splitlines() if line.startswith("clinic_booking_conflicts_total ")]
    assert conflicts and float(conflicts[0].split()[1]) >= 1
    assert 'http_requests_total{handler="/api/appointments"' in body


def test_latency_buckets_start_at_5ms(client):
    client.get("/api/doctors")
    assert 'http_request_duration_seconds_bucket{handler="/api/doctors",le="0.005"' in client.get("/metrics").text
