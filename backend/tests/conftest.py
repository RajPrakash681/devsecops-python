"""Test setup: a throwaway SQLite database, built by the real Alembic migrations.

DATABASE_URL is set before the app is imported, so the app (and its metrics collector) can
never reach a real PostgreSQL during tests.
"""
import os
import pathlib
import tempfile

_TMP = tempfile.mkdtemp(prefix="clinicflow-test-")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP}/test.db"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")  # the migration files are under test too
    yield


@pytest.fixture
def client(migrated_db):
    from fastapi.testclient import TestClient

    from app.db import engine
    from app.main import app

    with engine.begin() as conn:  # every test starts from an empty clinic
        for table in ("appointment_events", "appointments", "doctors"):
            conn.execute(text(f"DELETE FROM {table}"))  # noqa: S608 - fixed table names
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_doctor(client):
    def _make(name="Dr. Meera Iyer", specialty="General Medicine", room="101", active=True):
        r = client.post("/api/doctors", json={"name": name, "specialty": specialty, "room": room, "active": active})
        assert r.status_code == 201, r.text
        return r.json()
    return _make


@pytest.fixture
def book(client):
    def _book(doctor_id, starts_at, patient_name="Arjun Mehta", duration_min=30, expect=201, **extra):
        r = client.post("/api/appointments", json={
            "doctor_id": doctor_id, "patient_name": patient_name, "patient_phone": "+91 98765 43210",
            "reason": "follow-up", "starts_at": starts_at, "duration_min": duration_min, **extra})
        assert r.status_code == expect, r.text
        return r.json()
    return _book
