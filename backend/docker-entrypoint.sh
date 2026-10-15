#!/bin/sh
# 1. wait for Postgres  2. apply migrations (serialised by an advisory lock)  3. serve
set -e
python -m app.wait_for_db
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
