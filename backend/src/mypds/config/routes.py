import hashlib
from typing import Literal

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal, require_role
from mypds.auth.service import audit
from mypds.config.models import AppSetting, BrandingAsset, UserPreference, Wallpaper
from mypds.config.schemas import Branding, Preferences
from mypds.core.db import get_db
from mypds.core.http import client_ip, problem

router = APIRouter(prefix="/api/v1", tags=["config"])


async def load_preferences(db: AsyncSession, p: Principal) -> Preferences:
    row = await db.get(UserPreference, p.user.id)
    if row is None:
        return Preferences()
    return Preferences.model_validate({**Preferences().model_dump(), **row.data})


@router.get("/me/preferences", response_model=Preferences)
async def get_prefs(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    return await load_preferences(db, p)


@router.put("/me/preferences", response_model=Preferences)
async def put_prefs(body: Preferences, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    current = await load_preferences(db, p)
    # Les fonds d'écran ne se modifient que par import / suppression
    body.wallpaper_light, body.wallpaper_dark = current.wallpaper_light, current.wallpaper_dark
    await _save_prefs(db, p, body)
    await db.commit()
    return body


async def _save_prefs(db: AsyncSession, p: Principal, prefs: Preferences) -> None:
    row = await db.get(UserPreference, p.user.id)
    if row is None:
        db.add(UserPreference(user_id=p.user.id, data=prefs.model_dump()))
    else:
        row.data = prefs.model_dump()


MAX_WALLPAPER_BYTES = 8 * 1024 * 1024
Variant = Literal["light", "dark"]


@router.get("/me/wallpaper/{variant}")
async def get_wallpaper(
    variant: Variant, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    wp = await db.get(Wallpaper, (p.user.id, variant))
    if wp is None:
        raise problem(404, "Aucun fond d'écran importé")
    # Privé (cookie de session) ; l'URL change avec ?v=<empreinte>, d'où un cache long
    return Response(
        wp.data, media_type=wp.content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"}
    )


@router.put("/me/wallpaper/{variant}", response_model=Preferences)
async def put_wallpaper(
    variant: Variant, file: UploadFile, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    data = await file.read(MAX_WALLPAPER_BYTES + 1)
    if len(data) > MAX_WALLPAPER_BYTES:
        raise problem(413, "Image trop volumineuse (8 Mo maximum)")
    ctype = sniff_image(data)
    if ctype is None:
        raise problem(422, "Format non pris en charge : utilisez une image PNG, JPEG ou WebP")
    digest = hashlib.sha256(data).hexdigest()
    wp = await db.get(Wallpaper, (p.user.id, variant))
    if wp is None:
        db.add(Wallpaper(user_id=p.user.id, variant=variant, content_type=ctype, data=data, sha256=digest))
    else:
        wp.content_type, wp.data, wp.sha256 = ctype, data, digest
    prefs = await load_preferences(db, p)
    setattr(prefs, f"wallpaper_{variant}", digest[:12])
    prefs.background = "custom"  # un fond importé est affiché tout de suite
    await _save_prefs(db, p, prefs)
    await db.commit()
    return prefs


@router.delete("/me/wallpaper/{variant}", response_model=Preferences)
async def delete_wallpaper(
    variant: Variant, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    wp = await db.get(Wallpaper, (p.user.id, variant))
    if wp is not None:
        await db.delete(wp)
    prefs = await load_preferences(db, p)
    setattr(prefs, f"wallpaper_{variant}", None)
    if prefs.background == "custom" and not (prefs.wallpaper_light or prefs.wallpaper_dark):
        prefs.background = "nature"
    await _save_prefs(db, p, prefs)
    await db.commit()
    return prefs


@router.get("/branding", response_model=Branding)
async def get_branding(db: AsyncSession = Depends(get_db)):
    """Public : la page de connexion affiche le titre choisi (aucune donnée sensible)."""
    return await _branding(db)


@router.put("/branding", response_model=Branding)
async def put_branding(
    body: Branding,
    request: Request,
    p: Principal = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    current = await _branding(db)
    body.logo_version = current.logo_version  # géré uniquement par l'import du logo
    await _save_branding(db, body)
    await audit(db, "settings.branding", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return body


async def _branding(db: AsyncSession) -> Branding:
    row = await db.get(AppSetting, "branding")
    return Branding.model_validate(row.value) if row else Branding()


async def _save_branding(db: AsyncSession, value: Branding) -> None:
    row = await db.get(AppSetting, "branding")
    if row is None:
        db.add(AppSetting(key="branding", value=value.model_dump()))
    else:
        row.value = value.model_dump()


MAX_LOGO_BYTES = 512 * 1024


def sniff_image(data: bytes) -> str | None:
    """Type réel d'après la signature du fichier (PNG, JPEG, WebP). SVG refusé : il peut contenir du script."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/branding/logo")
async def get_logo(db: AsyncSession = Depends(get_db)):
    """Public (page de connexion). Mis en cache longtemps : l'URL change avec ?v=<empreinte>."""
    asset = await db.get(BrandingAsset, "logo")
    if asset is None:
        raise problem(404, "Aucun logo importé")
    return Response(
        asset.data,
        media_type=asset.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable", "Content-Disposition": "inline"},
    )


@router.put("/branding/logo", response_model=Branding)
async def put_logo(
    file: UploadFile,
    request: Request,
    p: Principal = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read(MAX_LOGO_BYTES + 1)
    if len(data) > MAX_LOGO_BYTES:
        raise problem(413, "Logo trop volumineux (512 Ko maximum)")
    ctype = sniff_image(data)
    if ctype is None:
        raise problem(422, "Format non pris en charge : utilisez une image PNG, JPEG ou WebP")
    digest = hashlib.sha256(data).hexdigest()
    asset = await db.get(BrandingAsset, "logo")
    if asset is None:
        db.add(BrandingAsset(key="logo", content_type=ctype, data=data, sha256=digest))
    else:
        asset.content_type, asset.data, asset.sha256 = ctype, data, digest
    branding = await _branding(db)
    branding.logo_version = digest[:12]
    branding.show_logo = True
    await _save_branding(db, branding)
    await audit(db, "settings.branding.logo", actor=p.user.id, ip=client_ip(request), details={"sha256": digest})
    await db.commit()
    return branding


@router.delete("/branding/logo", response_model=Branding)
async def delete_logo(
    request: Request, p: Principal = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)
):
    asset = await db.get(BrandingAsset, "logo")
    if asset is not None:
        await db.delete(asset)
    branding = await _branding(db)
    branding.logo_version = None
    await _save_branding(db, branding)
    await audit(db, "settings.branding.logo_reset", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return branding
