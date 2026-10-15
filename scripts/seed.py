#!/usr/bin/env python3
"""Load a realistic clinic into ClinicFlow through its public API (so validation runs too).

Four doctors, two weeks of finished history (for the no-show rate), and a full "today" whose
statuses follow the clock: earlier visits are completed or no-shows, the current slot is
checked in, later ones are booked. Tomorrow is partly booked ahead. Standard library only.

    python3 scripts/seed.py                                   # docker compose (localhost:8000)
    API=http://clinicflow.local python3 scripts/seed.py       # through the Kubernetes Ingress
"""
import json
import os
import random
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API = os.environ.get("API", "http://localhost:8000").rstrip("/")
HOST = os.environ.get("HOST_HEADER")
now = datetime.now(ZoneInfo(os.environ.get("CLINIC_TZ", "Asia/Kolkata"))).replace(tzinfo=None)
rng = random.Random(21)


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", **({"Host": HOST} if HOST else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 - URL comes from the operator
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


DOCTORS = [("Dr. Meera Iyer", "General Medicine", "101"), ("Dr. Kabir Rao", "Paediatrics", "102"),
           ("Dr. Sana Qureshi", "Dermatology", "201"), ("Dr. Vikram Nair", "Orthopaedics", "202")]
PATIENTS = ["Ananya Sharma", "Rohan Gupta", "Ishita Verma", "Aditya Singh", "Priya Nair", "Karan Malhotra",
            "Sneha Reddy", "Vivek Joshi", "Neha Kapoor", "Arjun Mehta", "Diya Patel", "Rahul Bose",
            "Kavya Menon", "Siddharth Rao", "Pooja Iyer", "Manav Khanna", "Tara Das", "Yash Agarwal",
            "Riya Chawla", "Nikhil Jain", "Aisha Khan", "Dev Sharma", "Meghna Pillai", "Farhan Ali"]
REASONS = {"General Medicine": ["fever for 3 days", "BP review", "diabetes follow-up", "cough and cold", "annual check-up"],
           "Paediatrics": ["vaccination", "growth check", "ear pain", "fever", "nutrition advice"],
           "Dermatology": ["acne follow-up", "skin rash", "hair fall", "mole check", "eczema review"],
           "Orthopaedics": ["knee pain", "back pain", "fracture review", "shoulder stiffness", "sports injury"]}


def phone():
    return f"+91 9{rng.randint(100000000, 999999999)}"


def book(doc, start, minutes=30):
    status, body = call("POST", "/api/appointments", {
        "doctor_id": doc["id"], "patient_name": rng.choice(PATIENTS), "patient_phone": phone(),
        "reason": rng.choice(REASONS[doc["specialty"]]), "starts_at": start.isoformat(timespec="minutes"),
        "duration_min": minutes})
    return body if status == 201 else None


def move(appt, *steps, note=""):
    for s in steps:
        call("POST", f"/api/appointments/{appt['id']}/status", {"status": s, "note": note})


print(f"Seeding {API}")
existing = {d["name"]: d for d in call("GET", "/api/doctors")[1]}
doctors = []
for name, specialty, room in DOCTORS:
    doc = existing.get(name) or call("POST", "/api/doctors", {"name": name, "specialty": specialty, "room": room})[1]
    doctors.append(doc)
    print(f"  doctor  {doc['id']:>3}  {name} ({specialty})")

# Two weeks of history: finished visits, about one in eight a no-show.
history = 0
for days_ago in range(14, 0, -1):
    day = (now - timedelta(days=days_ago)).replace(hour=8, minute=0, second=0, microsecond=0)
    if day.weekday() == 6:
        continue  # closed on Sundays
    for doc in doctors:
        for slot in rng.sample(range(26), 6):
            appt = book(doc, day + timedelta(minutes=30 * slot))
            if appt:
                history += 1
                move(appt, "NO_SHOW") if rng.random() < 0.12 else move(appt, "CHECKED_IN", "COMPLETED")
print(f"  history {history} finished appointments over the last two weeks")

# Tomorrow: already partly booked, as a real front desk would be.
tomorrow, count = now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1), 0
for doc in doctors:
    for slot in sorted(rng.sample(range(26), 9)):
        count += bool(book(doc, tomorrow + timedelta(minutes=30 * slot)))
print(f"  tomorrow {count} appointments booked ahead")

# Today: book the whole day first, then replay the front desk in time order so the audit
# trail reads like a real day. Statuses follow the clock.
today = now.replace(hour=8, minute=0, second=0, microsecond=0)
booked = []
for doc in doctors:
    for slot in sorted(rng.sample(range(26), 16)):
        appt = book(doc, today + timedelta(minutes=30 * slot), rng.choice([30, 30, 30, 60]) if slot < 25 else 30)
        if appt:
            booked.append(appt)
for appt in sorted(booked, key=lambda x: x["starts_at"]):
    start, end = datetime.fromisoformat(appt["starts_at"]), datetime.fromisoformat(appt["ends_at"])
    if end <= now:
        if rng.random() < 0.12:
            move(appt, "NO_SHOW", note="no answer on phone")
        else:
            move(appt, "CHECKED_IN", "COMPLETED", note=rng.choice(["", "", "prescription given", "review in 2 weeks"]))
    elif start <= now + timedelta(minutes=30):
        move(appt, "CHECKED_IN", note="arrived at reception")
    elif rng.random() < 0.08:
        move(appt, "CANCELLED", note="patient called to cancel")
count = len(booked)
print(f"  today   {count} appointments on {today:%d %b %Y}")

stats = call("GET", "/api/stats")[1]
print(f"  stats   {stats['by_status']}  waiting={stats['waiting_now']}  no-show 30d={stats['no_show_rate_30d']:.0%}")
