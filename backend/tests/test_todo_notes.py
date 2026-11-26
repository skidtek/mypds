"""Widgets Todo et Post-it : contenu par utilisateur et par widget, dates de création et de clôture."""

import httpx

from tests.conftest import login


async def test_todo_cycle(client) -> None:
    h = {"X-CSRF-Token": await login(client, "bob")}
    w = "w_todo1"
    a = (await client.post("/api/v1/todo", json={"widget": w, "text": " Acheter du pain "}, headers=h)).json()
    b = (await client.post("/api/v1/todo", json={"widget": w, "text": "Sauvegarder le NAS"}, headers=h)).json()
    assert a["text"] == "Acheter du pain" and a["created_at"] and a["done_at"] is None
    items = (await client.get(f"/api/v1/todo?widget={w}")).json()
    assert [i["id"] for i in items] == [b["id"], a["id"]]  # la plus récente en haut

    done = (await client.patch(f"/api/v1/todo/{a['id']}", json={"done": True}, headers=h)).json()
    assert done["done_at"]
    again = (await client.patch(f"/api/v1/todo/{a['id']}", json={"done": True}, headers=h)).json()
    assert again["done_at"] == done["done_at"]  # la date de clôture ne bouge pas
    items = (await client.get(f"/api/v1/todo?widget={w}")).json()
    assert items[-1]["id"] == a["id"]  # les terminées après les ouvertes

    reopened = (await client.patch(f"/api/v1/todo/{a['id']}", json={"done": False}, headers=h)).json()
    assert reopened["done_at"] is None
    await client.patch(f"/api/v1/todo/{b['id']}", json={"done": True}, headers=h)
    assert (await client.delete(f"/api/v1/todo?widget={w}&done_only=true", headers=h)).status_code == 204
    assert [i["id"] for i in (await client.get(f"/api/v1/todo?widget={w}")).json()] == [a["id"]]
    assert (await client.post("/api/v1/todo", json={"widget": "bad id", "text": "x"}, headers=h)).status_code == 422
    await client.delete(f"/api/v1/todo?widget={w}", headers=h)


async def test_notes_cycle(client) -> None:
    h = {"X-CSRF-Token": await login(client, "bob")}
    w = "w_note1"
    n1 = (await client.post("/api/v1/notes", json={"widget": w, "title": "Courses"}, headers=h)).json()
    n2 = (await client.post("/api/v1/notes", json={"widget": w, "color": "pink", "texture": "grid"}, headers=h)).json()
    assert n1["color"] == "yellow" and n1["texture"] == "plain" and n2["position"] == n1["position"] + 1
    up = (
        await client.patch(f"/api/v1/notes/{n1['id']}", json={"body": "Lait\nŒufs", "color": "blue"}, headers=h)
    ).json()
    assert up["body"] == "Lait\nŒufs" and up["color"] == "blue"
    bad = await client.patch(f"/api/v1/notes/{n1['id']}", json={"texture": "velvet"}, headers=h)
    assert bad.status_code == 422
    assert [n["id"] for n in (await client.get(f"/api/v1/notes?widget={w}")).json()] == [n1["id"], n2["id"]]
    assert (await client.delete(f"/api/v1/notes/{n2['id']}", headers=h)).status_code == 204
    await client.delete(f"/api/v1/notes?widget={w}", headers=h)
    assert (await client.get(f"/api/v1/notes?widget={w}")).json() == []


async def test_isolation_between_users(db_schema) -> None:
    from mypds.app import create_app

    app = create_app()
    a = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    b = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    async with a, b:
        ha = {"X-CSRF-Token": await login(a, "alice")}
        hb = {"X-CSRF-Token": await login(b, "bob")}
        t = (await a.post("/api/v1/todo", json={"widget": "w_x", "text": "secret"}, headers=ha)).json()
        n = (await a.post("/api/v1/notes", json={"widget": "w_x"}, headers=ha)).json()
        assert (await b.get("/api/v1/todo?widget=w_x")).json() == []
        assert (await b.patch(f"/api/v1/todo/{t['id']}", json={"done": True}, headers=hb)).status_code == 404
        assert (await b.delete(f"/api/v1/notes/{n['id']}", headers=hb)).status_code == 404
        await a.delete("/api/v1/todo?widget=w_x", headers=ha)
        await a.delete("/api/v1/notes?widget=w_x", headers=ha)
