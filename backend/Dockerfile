FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt requirements-ai.txt ./
ARG INSTALL_AI=false
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_AI" = "true" ]; then pip install --no-cache-dir -r requirements-ai.txt; fi
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY schema_check.py ./schema_check.py
# Fail the image build if a service or router is missing or cannot import.
RUN JWT_SECRET=release-build-validation-only-0123456789 python -m app.release_check
RUN useradd --uid 10001 --create-home appuser && mkdir -p /srv/media && chown appuser:appuser /srv/media
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
