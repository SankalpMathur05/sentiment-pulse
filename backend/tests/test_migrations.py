"""The hand-written Alembic migration must create exactly what the ORM models describe."""
from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db.base import Base


def test_migrations_match_orm_models(db_engine):
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, Base.metadata) == []
