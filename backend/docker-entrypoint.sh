#!/bin/sh
set -e

# Bring the schema up to date before serving traffic. Safe to run on every start:
# Alembic only applies migrations that have not been applied yet.
alembic upgrade head

# exec: uvicorn replaces the shell, so it receives stop signals directly and shuts down cleanly.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
