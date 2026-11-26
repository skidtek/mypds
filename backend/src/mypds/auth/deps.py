"""Dépendances FastAPI : utilisateur courant, CSRF, rôles."""

import hmac
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.models import ROLES, Session, User
from mypds.auth.service import load_session
from mypds.core.db import get_db
from mypds.core.http import problem
from mypds.core.settings import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def cookie_name() -> str:
    # Le préfixe __Host- impose Secure : utilisé dès que le cookie est sécurisé.
    return "__Host-mypds_session" if get_settings().cookie_secure else "mypds_session"


@dataclass(slots=True)
class Principal:
    user: User
    session: Session

    @property
    def role_level(self) -> int:
        return ROLES.index(self.user.role) if self.user.role in ROLES else -1


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        site = request.headers.get("sec-fetch-site")
        if site and site not in ("same-origin", "none"):
            raise problem(403, "Requête inter-sites refusée")
        return
    allowed = get_settings().public_origin
    origin_netloc = urlsplit(origin).netloc
    if allowed:
        if origin.rstrip("/") != allowed.rstrip("/"):
            raise problem(403, "Origine refusée")
    elif origin_netloc != request.headers.get("host"):
        raise problem(403, "Origine refusée")


async def current_principal(request: Request, db: AsyncSession = Depends(get_db)) -> Principal:
    token = request.cookies.get(cookie_name())
    if not token:
        raise problem(401, "Authentification requise")
    loaded = await load_session(db, token)
    if loaded is None:
        raise problem(401, "Session expirée")
    sess, user = loaded
    if request.method not in SAFE_METHODS:
        _check_origin(request)
        sent = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(sent, sess.csrf_token):
            raise problem(403, "Jeton CSRF invalide")
    return Principal(user=user, session=sess)


def require_role(role: str):  # type: ignore[no-untyped-def]
    level = ROLES.index(role)

    async def _dep(p: Principal = Depends(current_principal)) -> Principal:
        if p.role_level < level:
            raise problem(403, "Permission insuffisante")
        return p

    return _dep


check_origin = _check_origin
