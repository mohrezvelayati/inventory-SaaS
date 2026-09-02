# syntax=docker/dockerfile:1.7
FROM python:3.14.7-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.14.7-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=10000

RUN addgroup --system django && adduser --system --ingroup django django
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=django:django . .

RUN SECRET_KEY=build-only-secret-key \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres \
    python manage.py collectstatic --noinput

USER django
EXPOSE 10000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/app/docker/start.sh"]
