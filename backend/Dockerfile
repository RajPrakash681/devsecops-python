# ClinicFlow API - FastAPI on Python 3.12
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 app
WORKDIR /app

# Dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Never run as root. One uvicorn process per container: scale with replicas, not workers,
# so each pod exposes exactly one Prometheus registry.
USER 10001
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
