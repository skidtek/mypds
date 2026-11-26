"""Configuration des tests : base `mypds_test` sur le PostgreSQL de développement (scripts/dev-db.sh),
ou celle désignée par MYPDS_TEST_DATABASE_URL (CI), qui doit déjà exister."""

import os
import secrets
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_key = Path(tempfile.mkdtemp()) / "secret.key"
_key.write_bytes(secrets.token_bytes(32))
_LOCAL_DB = "MYPDS_TEST_DATABASE_URL" not in os.environ
os.environ.setdefault(
    "MYPDS_TEST_DATABASE_URL", f"postgresql+asyncpg://mypds@/mypds_test?host={ROOT}/.dev/run&port=5433"
)
os.environ["MYPDS_DATABASE_URL"] = os.environ["MYPDS_TEST_DATABASE_URL"]
os.environ["MYPDS_SECRET_KEY_FILE"] = str(_key)
os.environ["MYPDS_COOKIE_SECURE"] = "false"
os.environ["MYPDS_SCHEDULER_ENABLED"] = "false"

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402

from mypds.auth.models import User  # noqa: E402
from mypds.auth.service import hash_password  # noqa: E402
from mypds.core.db import get_engine, sessionmaker  # noqa: E402
from mypds.models import Base  # noqa: E402

PASSWORD = "correct-horse-battery"


async def _ensure_db() -> None:
    conn = await asyncpg.connect(host=str(ROOT / ".dev/run"), port=5433, user="mypds", database="postgres")
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='mypds_test'"):
            await conn.execute("CREATE DATABASE mypds_test")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
async def db_schema():
    if _LOCAL_DB:
        await _ensure_db()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with sessionmaker()() as db:
        db.add(User(username="alice", display_name="Alice", role="admin", password_hash=hash_password(PASSWORD)))
        db.add(User(username="bob", display_name="Bob", role="viewer", password_hash=hash_password(PASSWORD)))
        await db.commit()
    yield


@pytest.fixture
async def client(db_schema):
    from mypds.app import create_app

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def login(client: httpx.AsyncClient, username: str = "alice") -> str:
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]
