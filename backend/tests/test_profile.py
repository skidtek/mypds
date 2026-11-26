import httpx

from tests.conftest import PASSWORD, login
from tests.test_api import PNG_1PX


async def test_profile_name_and_avatar(client) -> None:
    csrf = await login(client, "bob")
    h = {"X-CSRF-Token": csrf}
    r = await client.patch("/api/v1/me", json={"display_name": "  Bobby  "}, headers=h)
    assert r.status_code == 200 and r.json()["display_name"] == "Bobby"
    assert (await client.put("/api/v1/me/avatar", files={"file": ("a.svg", b"<svg/>")}, headers=h)).status_code == 422
    up = await client.put("/api/v1/me/avatar", files={"file": ("me.png", PNG_1PX)}, headers=h)
    assert up.json()["avatar_version"]
    assert (await client.get("/api/v1/auth/me")).json()["avatar_version"] == up.json()["avatar_version"]
    assert (await client.get("/api/v1/me/avatar")).content == PNG_1PX
    assert (await client.delete("/api/v1/me/avatar", headers=h)).json()["avatar_version"] is None
    await client.patch("/api/v1/me", json={"display_name": "Bob"}, headers=h)


async def test_password_change_closes_other_sessions(db_schema) -> None:
    from mypds.app import create_app

    app = create_app()
    a = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    b = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    async with a, b:
        csrf_a = await login(a, "bob")
        await login(b, "bob")
        sessions = (await a.get("/api/v1/me/sessions")).json()
        assert len(sessions) >= 2 and sum(s["current"] for s in sessions) == 1
        h = {"X-CSRF-Token": csrf_a}
        wrong = await a.post("/api/v1/me/password", json={"current": "nope", "new": "another-long-pass"}, headers=h)
        assert wrong.status_code == 403
        short = await a.post("/api/v1/me/password", json={"current": PASSWORD, "new": "short"}, headers=h)
        assert short.status_code == 422
        ok = await a.post("/api/v1/me/password", json={"current": PASSWORD, "new": "another-long-pass"}, headers=h)
        assert ok.status_code == 204
        assert (await b.get("/api/v1/auth/me")).status_code == 401  # l'autre session est fermée
        assert (await a.get("/api/v1/auth/me")).status_code == 200  # la session courante reste ouverte
        back = await a.post("/api/v1/me/password", json={"current": "another-long-pass", "new": PASSWORD}, headers=h)
        assert back.status_code == 204


async def test_close_other_session(db_schema) -> None:
    from mypds.app import create_app

    app = create_app()
    a = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    b = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    async with a, b:
        csrf_a = await login(a, "alice")
        await login(b, "alice")
        h = {"X-CSRF-Token": csrf_a}
        sessions = (await a.get("/api/v1/me/sessions")).json()
        mine = next(s for s in sessions if s["current"])
        other = next(s for s in sessions if not s["current"])
        assert (await a.delete(f"/api/v1/me/sessions/{mine['id']}", headers=h)).status_code == 422
        assert (await a.delete("/api/v1/me/sessions/zz", headers=h)).status_code == 422
        assert (await a.delete(f"/api/v1/me/sessions/{other['id']}", headers=h)).status_code == 204
        assert (await b.get("/api/v1/auth/me")).status_code == 401


async def test_avatar_size_limit(client) -> None:
    from mypds.auth.profile import MAX_AVATAR_BYTES

    h = {"X-CSRF-Token": await login(client, "bob")}
    big = PNG_1PX + b"\0" * (MAX_AVATAR_BYTES - len(PNG_1PX) + 1)
    assert MAX_AVATAR_BYTES == 5 * 1024 * 1024
    assert (await client.put("/api/v1/me/avatar", files={"file": ("big.png", big)}, headers=h)).status_code == 413
    ok = PNG_1PX + b"\0" * (2 * 1024 * 1024)  # 2 Mo : accepté (au-delà de l'ancienne limite de 1 Mo)
    assert (await client.put("/api/v1/me/avatar", files={"file": ("ok.png", ok)}, headers=h)).status_code == 200
    await client.delete("/api/v1/me/avatar", headers=h)
