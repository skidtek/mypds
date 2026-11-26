from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, check_origin, cookie_name, current_principal
from mypds.auth.models import User
from mypds.auth.service import (
    audit,
    create_session,
    delete_session,
    normalize_username,
    record_attempt,
    too_many_failures,
    verify_password,
)
from mypds.core.db import get_db, utcnow
from mypds.core.http import client_ip, problem
from mypds.core.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = True


class MeOut(BaseModel):
    username: str
    display_name: str
    role: str
    csrf_token: str
    avatar_version: str | None = None


def _me(p: Principal) -> MeOut:
    return MeOut(
        username=p.user.username,
        display_name=p.user.display_name,
        role=p.user.role,
        csrf_token=p.session.csrf_token,
        avatar_version=p.user.avatar_version,
    )


@router.post("/login", response_model=MeOut)
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    check_origin(request)
    ip = client_ip(request)
    username = normalize_username(body.username)
    if await too_many_failures(db, username, ip):
        await audit(db, "auth.login", outcome="throttled", ip=ip, details={"username": username})
        await db.commit()
        raise problem(429, "Trop de tentatives. Réessayez dans quelques minutes.")
    user = await db.scalar(select(User).where(User.username == username))
    ok = verify_password(user, body.password)
    await record_attempt(db, username, ip, ok)
    if not ok or user is None:
        await audit(db, "auth.login", outcome="failure", ip=ip, details={"username": username})
        await db.commit()
        raise problem(401, "Identifiant ou mot de passe incorrect")
    token, sess = await create_session(
        db, user, trusted=body.remember, ip=ip, user_agent=request.headers.get("user-agent")
    )
    user.last_login_at = utcnow()
    await audit(db, "auth.login", actor=user.id, ip=ip)
    await db.commit()
    s = get_settings()
    response.set_cookie(
        cookie_name(),
        token,
        max_age=int((sess.expires_at - utcnow()).total_seconds()) if body.remember else None,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
    )
    return _me(Principal(user=user, session=sess))


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(cookie_name(), "")
    await delete_session(db, token)
    await audit(db, "auth.logout", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    response.delete_cookie(cookie_name(), path="/")


@router.get("/me", response_model=MeOut)
async def me(p: Principal = Depends(current_principal)):
    return _me(p)
