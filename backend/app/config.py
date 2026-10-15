"""Settings come from the environment (Docker Compose / Kubernetes ConfigMap + Secret)."""
import os
from zoneinfo import ZoneInfo

from sqlalchemy.engine import URL


def database_url() -> str:
    # A full DATABASE_URL wins (tests, running the backend by hand). In Kubernetes the parts
    # arrive separately: host/db/user from the ConfigMap, the password from a Secret.
    if url := os.environ.get("DATABASE_URL"):
        return url
    # URL.create escapes special characters in the password; an f-string would not.
    return URL.create(
        "postgresql+psycopg",
        username=os.environ.get("DB_USER", "clinicflow"),
        password=os.environ.get("DB_PASSWORD", ""),
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ.get("DB_NAME", "clinicflow"),
    ).render_as_string(hide_password=False)


APP_ENV = os.environ.get("APP_ENV", "dev")
APP_VERSION = os.environ.get("APP_VERSION", "dev")
CORS_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]

# Appointment times are stored as clinic-local wall-clock time; "today" is the clinic's today.
CLINIC_TZ = ZoneInfo(os.environ.get("CLINIC_TZ", "Asia/Kolkata"))
OPENING_HOUR = int(os.environ.get("CLINIC_OPENING_HOUR", "9"))
CLOSING_HOUR = int(os.environ.get("CLINIC_CLOSING_HOUR", "18"))
SLOT_MINUTES = int(os.environ.get("CLINIC_SLOT_MINUTES", "30"))
