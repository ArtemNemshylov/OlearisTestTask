FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY app /app/app
COPY alembic.ini /app/
COPY alembic /app/alembic

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000

