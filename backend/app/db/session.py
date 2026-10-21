from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        # Check a pooled connection is alive before using it, so a database restart or an
        # idle-connection timeout on the host does not surface as a failed request.
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 3,  # seconds: fail fast so requests return 503 instead of hanging
            "options": "-c timezone=UTC",  # timestamps come back (and are bucketed) in UTC
        },
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False keeps attribute values after commit, so building the response
    # from a just-saved row does not trigger another SELECT.
    return sessionmaker(bind=engine, expire_on_commit=False)
