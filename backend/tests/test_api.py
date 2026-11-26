from tests.conftest import PASSWORD, login


async def test_requires_auth(client) -> None:
    assert (await client.get("/api/v1/landing/layout")).status_code == 401
    assert (await client.get("/api/v1/rss/items")).status_code == 401


async def test_login_me_logout(client) -> None:
    csrf = await login(client)
    me = (await client.get("/api/v1/auth/me")).json()
    assert me["username"] == "alice" and me["csrf_token"] == csrf
    assert "password" not in str(me)
    assert (await client.post("/api/v1/auth/logout")).status_code == 403  # sans jeton CSRF
    assert (await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})).status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_cross_origin_login_refused(client) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


async def test_rate_limit(client) -> None:
    for _ in range(5):
        r = await client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope-nope-nope"})
        assert r.status_code == 401
    r = await client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope-nope-nope"})
    assert r.status_code == 429
    # L'IP est aussi bloquée pour les autres comptes pendant la fenêtre
    r = await client.post("/api/v1/auth/login", json={"username": "alice", "password": PASSWORD})
    assert r.status_code == 429
    from sqlalchemy import delete

    from mypds.auth.models import LoginAttempt
    from mypds.core.db import sessionmaker

    async with sessionmaker()() as db:
        await db.execute(delete(LoginAttempt))
        await db.commit()


async def test_landing_layout_cycle(client) -> None:
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    got = (await client.get("/api/v1/landing/layout")).json()
    doc = got["document"]
    doc["widgets"][0]["hidden"] = True
    r = await client.put("/api/v1/landing/layout", json={"revision": got["revision"], "document": doc}, headers=h)
    assert r.status_code == 200 and r.json()["revision"] == got["revision"] + 1
    stale = await client.put("/api/v1/landing/layout", json={"revision": got["revision"], "document": doc}, headers=h)
    assert stale.status_code == 409
    bad = dict(doc, widgets=[dict(doc["widgets"][0], type="iframe")])
    assert (
        await client.put("/api/v1/landing/layout", json={"revision": 99, "document": bad}, headers=h)
    ).status_code == 422
    reset = await client.post("/api/v1/landing/layout/reset", headers=h)
    assert reset.json()["document"]["widgets"][0]["hidden"] is False


async def test_preferences_and_branding(client) -> None:
    csrf = await login(client, "bob")
    h = {"X-CSRF-Token": csrf}
    prefs = (await client.get("/api/v1/me/preferences")).json()
    prefs["background"] = "it"
    assert (await client.put("/api/v1/me/preferences", json=prefs, headers=h)).json()["background"] == "it"
    prefs["search_engine"], prefs["search_custom_url"] = "custom", "javascript:alert(1)%s"
    assert (await client.put("/api/v1/me/preferences", json=prefs, headers=h)).status_code == 422
    assert (await client.get("/api/v1/branding")).status_code == 200  # public
    r = await client.put("/api/v1/branding", json={"title": "X"}, headers=h)
    assert r.status_code == 403  # viewer


async def test_internal_feed_refused(client) -> None:
    csrf = await login(client)
    r = await client.post(
        "/api/v1/rss/feeds", json={"url": "http://192.168.1.10:8006/"}, headers={"X-CSRF-Token": csrf}
    )
    assert r.status_code == 422 and "non autorisée" in r.json()["detail"]


async def test_calendar_url_never_returned(client, monkeypatch) -> None:
    from mypds.widgets.calendar import service

    async def fake_fetch(self, url, etag=None, last_modified=None, auth=None):  # noqa: ANN001, ANN202
        from httpx import Headers

        from mypds.core.net import FetchResult
        from tests.test_calendar import ICS

        return FetchResult(200, Headers(), ICS.encode(), url)

    monkeypatch.setattr(service.IcsProvider, "fetch", fake_fetch)
    csrf = await login(client)
    url = "https://cal.example/private/very-secret-token/basic.ics"
    r = await client.post(
        "/api/v1/calendar/sources", json={"name": "Perso", "url": url}, headers={"X-CSRF-Token": csrf}
    )
    assert r.status_code == 201, r.text
    assert "very-secret-token" not in r.text and r.json()["url_host"] == "cal.example"
    listing = await client.get("/api/v1/calendar/sources")
    assert "very-secret-token" not in listing.text
    assert (await client.get("/api/v1/calendar/events?days=60")).status_code == 200


async def test_security_headers(client) -> None:
    r = await client.get("/healthz")
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201e2b5f0d80000000049454e44ae426082"
)


async def test_logo_upload_cycle(client) -> None:
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    r = await client.put("/api/v1/branding/logo", files={"file": ("x.svg", svg, "image/svg+xml")}, headers=h)
    assert r.status_code == 422  # SVG refusé, même déclaré comme image
    fake = await client.put("/api/v1/branding/logo", files={"file": ("x.png", b"<html>", "image/png")}, headers=h)
    assert fake.status_code == 422  # signature vérifiée, pas l'extension
    big = await client.put("/api/v1/branding/logo", files={"file": ("x.png", PNG_1PX + b"0" * 600_000)}, headers=h)
    assert big.status_code == 413
    ok = await client.put("/api/v1/branding/logo", files={"file": ("logo.png", PNG_1PX, "image/png")}, headers=h)
    assert ok.status_code == 200 and ok.json()["logo_version"]
    # La version ne peut pas être forgée via PUT /branding
    b = ok.json() | {"logo_version": "forged", "title": "Maison"}
    assert (await client.put("/api/v1/branding", json=b, headers=h)).json()["logo_version"] == ok.json()["logo_version"]
    client.cookies.clear()
    pub = await client.get("/api/v1/branding/logo")  # public, pour la page de connexion
    assert pub.status_code == 200 and pub.headers["content-type"] == "image/png" and pub.content == PNG_1PX
    csrf = await login(client)
    gone = await client.delete("/api/v1/branding/logo", headers={"X-CSRF-Token": csrf})
    assert gone.json()["logo_version"] is None
    assert (await client.get("/api/v1/branding/logo")).status_code == 404


async def test_logo_admin_only(client) -> None:
    csrf = await login(client, "bob")
    r = await client.put("/api/v1/branding/logo", files={"file": ("l.png", PNG_1PX)}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 403


async def test_wallpapers_per_user_and_variant(client) -> None:
    csrf = await login(client, "bob")
    h = {"X-CSRF-Token": csrf}
    r = await client.put("/api/v1/me/wallpaper/light", files={"file": ("w.png", PNG_1PX)}, headers=h)
    assert r.status_code == 200 and r.json()["wallpaper_light"] and r.json()["wallpaper_dark"] is None
    assert (
        await client.put("/api/v1/me/wallpaper/sepia", files={"file": ("w.png", PNG_1PX)}, headers=h)
    ).status_code == 422
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>"
    assert (await client.put("/api/v1/me/wallpaper/dark", files={"file": ("w.svg", svg)}, headers=h)).status_code == 422
    # Les empreintes ne se forgent pas via les préférences
    assert r.json()["background"] == "custom"
    prefs = r.json() | {"wallpaper_dark": "forged", "color_mode": "light"}
    saved = (await client.put("/api/v1/me/preferences", json=prefs, headers=h)).json()
    assert saved["wallpaper_dark"] is None and saved["color_mode"] == "light"
    assert (await client.get("/api/v1/me/wallpaper/light")).content == PNG_1PX
    assert (await client.get("/api/v1/me/wallpaper/dark")).status_code == 404
    # Privé : un autre utilisateur ne voit pas ce fond
    client.cookies.clear()
    await login(client, "alice")
    assert (await client.get("/api/v1/me/wallpaper/light")).status_code == 404
    client.cookies.clear()
    csrf = await login(client, "bob")
    gone = await client.delete("/api/v1/me/wallpaper/light", headers={"X-CSRF-Token": csrf})
    assert gone.json()["wallpaper_light"] is None and gone.json()["background"] == "nature"


async def test_calendar_with_credentials(client, monkeypatch) -> None:
    from httpx import Headers

    from mypds.core.net import FetchResult
    from mypds.widgets.calendar import service
    from tests.test_calendar import ICS

    seen: list[tuple[str, object]] = []

    async def fake_net_fetch(url, *, max_bytes, headers=None, timeout=15, basic_auth=None, max_redirects=3):  # noqa: ANN001, ANN202
        seen.append((url, basic_auth))
        status = 200 if basic_auth == ("jdupont", "s3cret") else 401
        return FetchResult(status, Headers(), ICS.encode() if status == 200 else b"", url)

    monkeypatch.setattr(service.net, "fetch", fake_net_fetch)
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    url = "https://jdupont@dav.example.org/SOGo/dav/jdupont/Calendar/personal.ics"
    no_pw = await client.post("/api/v1/calendar/sources", json={"name": "Travail", "url": url}, headers=h)
    assert no_pw.status_code == 422 and "Mot de passe requis" in no_pw.json()["detail"]
    bad = await client.post(
        "/api/v1/calendar/sources", json={"name": "Travail", "url": url, "password": "x"}, headers=h
    )
    assert bad.status_code == 422 and "Accès refusé" in bad.json()["detail"]
    ok = await client.post(
        "/api/v1/calendar/sources", json={"name": "Travail", "url": url, "password": "s3cret"}, headers=h
    )
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["auth_username"] == "jdupont" and "s3cret" not in ok.text and body["last_error"] is None
    # L'identifiant a été retiré de l'URL stockée et envoyé séparément
    assert seen[-1] == ("https://dav.example.org/SOGo/dav/jdupont/Calendar/personal.ics", ("jdupont", "s3cret"))
    listing = await client.get("/api/v1/calendar/sources")
    assert "s3cret" not in listing.text
    # Changer le seul mot de passe conserve l'identifiant et revalide
    upd = await client.patch(f"/api/v1/calendar/sources/{body['id']}", json={"password": "wrong"}, headers=h)
    assert upd.status_code == 422
    cleared = await client.patch(f"/api/v1/calendar/sources/{body['id']}", json={"clear_auth": True}, headers=h)
    assert cleared.status_code == 422  # le serveur exige une connexion : refus explicite


async def test_branding_logo_position(client) -> None:
    h = {"X-CSRF-Token": await login(client)}  # administrateur
    before = (await client.get("/api/v1/branding")).json()
    assert before["logo_position"] == "top"  # valeur par défaut (marques enregistrées avant ce réglage)
    r = await client.put("/api/v1/branding", json={**before, "logo_position": "left"}, headers=h)
    assert r.status_code == 200 and r.json()["logo_position"] == "left"
    bad = await client.put("/api/v1/branding", json={**before, "logo_position": "bottom"}, headers=h)
    assert bad.status_code == 422
    await client.put("/api/v1/branding", json=before, headers=h)
