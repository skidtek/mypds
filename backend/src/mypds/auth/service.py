"""Mots de passe, sessions, limitation des tentatives, audit."""

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.models import AuditLog, LoginAttempt, Session, User
from mypds.core.db import utcnow
from mypds.core.settings import get_settings

_hasher = PasswordHasher()  # Argon2id, paramètres par défaut conformes OWASP
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)
TOUCH_INTERVAL = timedelta(minutes=5)
MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères")
    return _hasher.hash(password)


def verify_password(user: User | None, password: str) -> bool:
    """Vérification à temps quasi constant, même si l'utilisateur n'existe pas."""
    try:
        _hasher.verify(user.password_hash if user else _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False
    return user is not None and user.is_active


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()


async def too_many_failures(db: AsyncSession, username: str, ip: str) -> bool:
    since = utcnow() - FAILURE_WINDOW
    q = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.ts >= since,
            LoginAttempt.success.is_(False),
            (LoginAttempt.username == username) | (LoginAttempt.ip == ip),
        )
    )
    return (await db.scalar(q) or 0) >= MAX_FAILURES


async def record_attempt(db: AsyncSession, username: str, ip: str, success: bool) -> None:
    db.add(LoginAttempt(username=username[:64], ip=ip, success=success))


def _lifetime(trusted: bool) -> timedelta:
    s = get_settings()
    return timedelta(days=s.session_days_trusted) if trusted else timedelta(hours=s.session_hours_default)


async def create_session(
    db: AsyncSession, user: User, *, trusted: bool, ip: str, user_agent: str | None
) -> tuple[str, Session]:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    sess = Session(
        id_hash=token_hash(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        trusted=trusted,
        created_at=now,
        last_seen_at=now,
        expires_at=now + _lifetime(trusted),
        ip=ip,
        user_agent=(user_agent or "")[:300],
    )
    db.add(sess)
    return token, sess


async def load_session(db: AsyncSession, token: str) -> tuple[Session, User] | None:
    sess = await db.get(Session, token_hash(token))
    now = utcnow()
    if sess is None or sess.expires_at <= now:
        return None
    user = await db.get(User, sess.user_id)
    if user is None or not user.is_active:
        return None
    if now - sess.last_seen_at > TOUCH_INTERVAL:  # expiration glissante
        sess.last_seen_at = now
        sess.expires_at = now + _lifetime(sess.trusted)
        await db.commit()
    return sess, user


async def delete_session(db: AsyncSession, token: str) -> None:
    await db.execute(delete(Session).where(Session.id_hash == token_hash(token)))


async def purge_expired(db: AsyncSession) -> None:
    await db.execute(delete(Session).where(Session.expires_at <= utcnow()))
    await db.execute(delete(LoginAttempt).where(LoginAttempt.ts <= utcnow() - timedelta(days=30)))


async def audit(
    db: AsyncSession,
    action: str,
    *,
    outcome: str = "success",
    actor: uuid.UUID | None = None,
    ip: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            outcome=outcome,
            actor_user_id=actor,
            actor_ip=ip,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
    )
