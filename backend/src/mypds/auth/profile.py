"""Profil de l'utilisateur connecté : nom affiché, photo, mot de passe, sessions."""

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.auth.models import Session, UserAvatar
from mypds.auth.routes import MeOut, _me
from mypds.auth.service import (
    audit,
    hash_password,
    record_attempt,
    too_many_failures,
    verify_password,
)
from mypds.config.routes import sniff_image
from mypds.core.db import get_db, utcnow
from mypds.core.http import client_ip, problem

router = APIRouter(prefix="/api/v1/me", tags=["profile"])
MAX_AVATAR_BYTES = 5 * 1024 * 1024


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class PasswordIn(BaseModel):
    current: str = Field(min_length=1, max_length=256)
    new: str = Field(min_length=12, max_length=256)


class SessionOut(BaseModel):
    id: str
    current: bool
    trusted: bool
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip: str | None
    user_agent: str | None


@router.patch("", response_model=MeOut)
async def update_profile(
    body: ProfileIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    p.user.display_name = body.display_name.strip()
    await db.commit()
    return _me(p)


@router.get("/avatar")
async def get_avatar(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    av = await db.get(UserAvatar, p.user.id)
    if av is None:
        raise problem(404, "Aucune photo")
    return Response(
        av.data, media_type=av.content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"}
    )


@router.put("/avatar", response_model=MeOut)
async def put_avatar(file: UploadFile, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    data = await file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise problem(413, "Photo trop volumineuse (5 Mo maximum)")
    ctype = sniff_image(data)
    if ctype is None:
        raise problem(422, "Format non pris en charge : utilisez une image PNG, JPEG ou WebP")
    digest = hashlib.sha256(data).hexdigest()
    av = await db.get(UserAvatar, p.user.id)
    if av is None:
        db.add(UserAvatar(user_id=p.user.id, content_type=ctype, data=data, sha256=digest))
    else:
        av.content_type, av.data, av.sha256 = ctype, data, digest
    p.user.avatar_version = digest[:12]
    await db.commit()
    return _me(p)


@router.delete("/avatar", response_model=MeOut)
async def delete_avatar(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(UserAvatar).where(UserAvatar.user_id == p.user.id))
    p.user.avatar_version = None
    await db.commit()
    return _me(p)


@router.post("/password", status_code=204)
async def change_password(
    body: PasswordIn, request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    """Exige le mot de passe actuel ; déconnecte toutes les autres sessions."""
    ip = client_ip(request)
    if await too_many_failures(db, p.user.username, ip):
        raise problem(429, "Trop de tentatives. Réessayez dans quelques minutes.")
    if not verify_password(p.user, body.current):
        await record_attempt(db, p.user.username, ip, False)
        await audit(db, "auth.password_change", outcome="failure", actor=p.user.id, ip=ip)
        await db.commit()
        raise problem(403, "Mot de passe actuel incorrect")
    if body.new == body.current:
        raise problem(422, "Le nouveau mot de passe doit être différent de l'actuel")
    try:
        p.user.password_hash = hash_password(body.new)
    except ValueError as exc:
        raise problem(422, str(exc)) from exc
    await db.execute(delete(Session).where(Session.user_id == p.user.id, Session.id_hash != p.session.id_hash))
    await audit(db, "auth.password_change", actor=p.user.id, ip=ip)
    await db.commit()


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(Session)
            .where(Session.user_id == p.user.id, Session.expires_at > utcnow())
            .order_by(Session.last_seen_at.desc())
        )
    ).all()
    return [
        SessionOut(
            id=s.id_hash[:16],
            current=s.id_hash == p.session.id_hash,
            trusted=s.trusted,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            expires_at=s.expires_at,
            ip=s.ip,
            user_agent=s.user_agent,
        )
        for s in rows
    ]


@router.delete("/sessions/{sid}", status_code=204)
async def close_session(
    sid: str, request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    """Ferme une autre session de l'utilisateur (l'identifiant est un préfixe de l'empreinte, jamais le jeton)."""
    if len(sid) != 16 or not all(c in "0123456789abcdef" for c in sid):
        raise problem(422, "Identifiant de session invalide")
    if p.session.id_hash.startswith(sid):
        raise problem(422, "Utilisez « Se déconnecter » pour fermer la session actuelle")
    result = await db.execute(delete(Session).where(Session.user_id == p.user.id, Session.id_hash.startswith(sid)))
    if not result.rowcount:
        raise problem(404, "Session introuvable")
    await audit(db, "auth.session_close", actor=p.user.id, ip=client_ip(request))
    await db.commit()
