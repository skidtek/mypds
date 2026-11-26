"""Fabrique de l'application FastAPI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from mypds import __version__
from mypds.alerts.routes import router as alerts_router
from mypds.auth.profile import router as profile_router
from mypds.auth.routes import router as auth_router
from mypds.cockpit.routes import router as cockpit_router
from mypds.config.routes import router as config_router
from mypds.connectors.routes import router as connectors_router
from mypds.connectors.service import loop as connector_loop
from mypds.core.db import dispose_engine, sessionmaker
from mypds.core.http import SecurityHeadersMiddleware
from mypds.core.logs import setup_logging
from mypds.core.scheduler import scheduler
from mypds.core.settings import get_settings
from mypds.landing.routes import router as landing_router
from mypds.widgets.calendar.routes import router as calendar_router
from mypds.widgets.notes.routes import router as notes_router
from mypds.widgets.rss.routes import router as rss_router
from mypds.widgets.todo.routes import router as todo_router
from mypds.widgets.weather.routes import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    s = get_settings()
    setup_logging(s.log_level)
    if s.scheduler_enabled:
        scheduler.start()
        connector_loop.start()
    yield
    await connector_loop.stop()
    await scheduler.stop()
    await dispose_engine()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="My Personal Digital Space",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if s.dev_mode else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.dev_mode else None,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    for r in (
        auth_router,
        profile_router,
        config_router,
        landing_router,
        weather_router,
        calendar_router,
        rss_router,
        connectors_router,
        cockpit_router,
        alerts_router,
        todo_router,
        notes_router,
    ):
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> JSONResponse:
        checks: dict[str, str] = {}
        try:
            async with sessionmaker()() as db:
                await db.execute(text("SELECT 1"))
                rev = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            checks["database"] = "ok"
            checks["migration"] = rev or "absente"
        except Exception as exc:  # noqa: BLE001
            checks["database"] = f"erreur : {type(exc).__name__}"
        checks["scheduler"] = "ok" if scheduler.running or not s.scheduler_enabled else "arrêté"
        ok = checks["database"] == "ok" and checks["scheduler"] == "ok"
        return JSONResponse({"status": "ok" if ok else "degraded", **checks}, status_code=200 if ok else 503)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):  # noqa: ANN001, ANN202
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": getattr(exc, "detail", "Introuvable")}, status_code=404)
        index = s.static_dir / "index.html" if s.static_dir else None
        if index and index.exists():  # routage côté client (SPA)
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return JSONResponse({"detail": "Introuvable"}, status_code=404)

    if s.static_dir and Path(s.static_dir).exists():
        app.mount("/", StaticFiles(directory=s.static_dir, html=True), name="static")
    return app
