import httpx

from mypds.core.settings import get_settings


async def test_spa_fallback_and_assets(db_schema, tmp_path, monkeypatch) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=app></div>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(get_settings(), "static_dir", tmp_path)
    from mypds.app import create_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://t") as c:
        assert "id=app" in (await c.get("/")).text
        assert "id=app" in (await c.get("/reglages")).text  # route côté client
        assert (await c.get("/assets/app.js")).status_code == 200
        api404 = await c.get("/api/v1/inexistant")
        assert api404.status_code == 404 and api404.headers["content-type"].startswith("application/json")
        assert "default-src 'self'" in (await c.get("/")).headers["content-security-policy"]
