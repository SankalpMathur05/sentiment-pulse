from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent of every ORM model; `Base.metadata` is what Alembic compares against."""
