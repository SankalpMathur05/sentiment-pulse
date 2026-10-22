# syntax=docker/dockerfile:1
# Build from the REPOSITORY ROOT so the image can include ml/ and artifacts/:
#   docker build -f backend/Dockerfile -t sentiment-pulse-api .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Dependencies first: these layers are reused from cache when only application code changes.
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# The shared ML package (cleaning + inference). Runtime dependencies only, no [train] extra;
# they are already satisfied by the pinned versions installed above.
COPY ml/ /tmp/ml/
RUN pip install /tmp/ml && rm -rf /tmp/ml

COPY artifacts/models/ /app/artifacts/models/
COPY backend/alembic.ini ./
COPY backend/alembic/ ./alembic/
COPY backend/app/ ./app/
COPY backend/docker-entrypoint.sh ./

ENV MODEL_DIR=/app/artifacts/models/tfidf-logreg-1.0.0

# Run as an unprivileged user: a compromised process cannot modify the image's files.
# (chmod in a RUN step rather than COPY --chmod, which some hosted builders don't support.)
RUN chmod 755 docker-entrypoint.sh && useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
