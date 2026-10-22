from datetime import datetime, timezone
from sqlalchemy import create_engine, event, DateTime, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .core.config import settings


def utcnow():
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """TIMESTAMPTZ on PostgreSQL; always timezone-aware UTC values in Python."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timezone-aware timestamp is required.")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )


class Base(DeclarativeBase):
    pass


def make_engine(url):
    engine = create_engine(
        url,
        connect_args=(
            {"check_same_thread": False, "timeout": 30}
            if url.startswith("sqlite")
            else {}
        ),
        pool_pre_ping=True,
        hide_parameters=True,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_connect(dbapi_connection, _):
            dbapi_connection.isolation_level = None
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
            dbapi_connection.execute("PRAGMA journal_mode=WAL")

        @event.listens_for(engine, "begin")
        def sqlite_begin(conn):
            # SQLite demo serializes transactions. PostgreSQL uses row locks instead.
            conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
