from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    # UTC naive in storage; API adds explicit Z. Avoid SQLite/Postgres timezone divergence.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    nim: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(12), default="student")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_version: Mapped[int] = mapped_column(Integer, default=1)
    face_template: Mapped[bytes | None] = mapped_column(LargeBinary)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    secret_hash: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    problem: Mapped[str] = mapped_column(String(240), default="")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    boot_id: Mapped[str | None] = mapped_column(String(80))
    veyon_host: Mapped[str] = mapped_column(String(253), default="")


class Enrollment(Base):
    __tablename__ = "enrollment_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    name: Mapped[str] = mapped_column(String(80))
    veyon_host: Mapped[str] = mapped_column(String(253), default="")


class LabSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    method: Mapped[str] = mapped_column(String(12))
    request_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_digest: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    end_reason: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(20), default="active")
    __table_args__ = (
        Index("one_open_session_per_user", "user_id", unique=True,
              postgresql_where=text("ended_at IS NULL"), sqlite_where=text("ended_at IS NULL")),
        Index("one_open_session_per_device", "device_id", unique=True,
              postgresql_where=text("ended_at IS NULL"), sqlite_where=text("ended_at IS NULL")),
    )


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(String(500), default="")


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    until: Mapped[datetime] = mapped_column(DateTime)


class Challenge(Base):
    __tablename__ = "face_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    nim: Mapped[str] = mapped_column(String(40))
    direction: Mapped[str] = mapped_column(String(10))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
