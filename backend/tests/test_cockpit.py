import uuid

import pytest
from pydantic import ValidationError

from mypds.cockpit.schema import CockpitLayout, default_layout
from tests.conftest import login

CID = str(uuid.uuid4())


def doc(tiles: list[dict]) -> dict:
    return {
        "schema": "mypds.cockpit-layout",
        "version": 1,
        "groups": [{"id": "g_a", "title": "A", "rows": [{"id": "r_a", "tiles": tiles}]}],
    }


def test_default_layout_without_and_with_connector() -> None:
    empty = default_layout([]).dump()
    assert [g["title"] for g in empty["groups"]] == ["Accueil", "Infrastructure", "Services"]
    from mypds.connectors.proxmox import demo
    from mypds.connectors.proxmox.connector import build_summary

    full = default_layout([(CID, build_summary(demo.cluster_status(), demo.cluster_resources()))]).dump()
    types = [t["type"] for g in full["groups"] for r in g["rows"] for t in r["tiles"]]
    assert types.count("proxmox.summary") == 1 and types.count("proxmox.node") == 2 and "proxmox.guest" in types


@pytest.mark.parametrize(
    "tile",
    [
        {"id": "t_1", "type": "iframe", "config": {}},
        {"id": "t_1", "type": "link", "config": {"label": "x", "url": "javascript:alert(1)"}},
        {"id": "t_1", "type": "proxmox.guest", "config": {"connector_id": CID, "guest": "lxc/1; drop"}},
        {"id": "t_1", "type": "proxmox.node", "config": {"connector_id": CID, "node": "../etc"}},
        {"id": "t_1", "type": "link", "config": {"label": "x", "url": "https://a", "token": "secret"}},
        {"id": "t_1", "type": "link", "width": {"desktop": 13}, "config": {"label": "x", "url": "https://a"}},
    ],
)
def test_rejects_bad_tiles(tile: dict) -> None:
    with pytest.raises(ValidationError):
        CockpitLayout.model_validate(doc([tile]))


def test_accepts_guest_tile_with_icon_and_url() -> None:
    t = {
        "id": "t_1",
        "type": "proxmox.guest",
        "width": {"desktop": 3},
        "config": {
            "connector_id": CID,
            "guest": "lxc/105",
            "url": "https://ha.home.lan",
            "icon": {"kind": "simple", "value": "homeassistant"},
        },
    }
    assert CockpitLayout.model_validate(doc([t])).groups[0].rows[0].tiles[0].config["url"] == "https://ha.home.lan"


def test_duplicate_ids_rejected() -> None:
    t = {"id": "t_1", "type": "link", "config": {"label": "x", "url": "https://a"}}
    with pytest.raises(ValidationError):
        CockpitLayout.model_validate(doc([t, dict(t)]))


async def test_connector_admin_and_demo_flow(client) -> None:
    csrf = await login(client, "bob")
    assert (await client.get("/api/v1/connectors")).status_code == 403  # viewer
    client.cookies.clear()
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    bad = await client.post(
        "/api/v1/connectors", json={"type": "proxmox", "name": "PVE", "config": {"mode": "live"}}, headers=h
    )
    assert bad.status_code == 422
    live = await client.post(
        "/api/v1/connectors",
        json={
            "type": "proxmox",
            "name": "PVE réel",
            "enabled": False,
            "config": {"mode": "live", "host": "192.0.2.62", "token_id": "mypds@pve!monitor"},
            "secrets": {"token_secret": "11111111-2222-3333-4444-555555555555"},
        },
        headers=h,
    )
    assert live.status_code == 201 and "11111111" not in live.text and live.json()["secrets_set"] == ["token_secret"]
    r = await client.post(
        "/api/v1/connectors", json={"type": "proxmox", "name": "Démo", "config": {"mode": "demo"}}, headers=h
    )
    assert r.status_code == 201 and r.json()["demo"] is True and r.json()["status"] == "ok"
    cid = r.json()["id"]
    snaps = (await client.get("/api/v1/connectors/snapshots")).json()
    demo_snap = next(s for s in snaps if s["id"] == cid)
    assert demo_snap["demo"] is True and demo_snap["data"]["cluster"]["name"] == "demo-cluster"
    hist = await client.get(f"/api/v1/connectors/{cid}/history", params={"resource": "node/pve01"})
    assert hist.status_code == 200 and hist.json()["demo"] is True and hist.json()["points"]
    test = (await client.post(f"/api/v1/connectors/{cid}/test", headers=h)).json()
    assert test["ok"] is True
    # Le secret reste inchangé si le champ est laissé vide
    upd = await client.patch(
        f"/api/v1/connectors/{live.json()['id']}", json={"name": "PVE", "secrets": {"token_secret": ""}}, headers=h
    )
    assert upd.json()["secrets_set"] == ["token_secret"]
    # La disposition par défaut est pré-remplie avec le connecteur de démo
    await client.post("/api/v1/cockpit/layout/reset", headers=h)
    layout = (await client.get("/api/v1/cockpit/layout")).json()["document"]
    assert any(t["type"] == "proxmox.summary" for g in layout["groups"] for r in g["rows"] for t in r["tiles"])
    for c in (await client.get("/api/v1/connectors")).json():
        await client.delete(f"/api/v1/connectors/{c['id']}", headers=h)


async def test_icon_upload_private(client) -> None:
    from tests.test_api import PNG_1PX

    csrf = await login(client)
    up = await client.post(
        "/api/v1/cockpit/icons", files={"file": ("grr.png", PNG_1PX)}, headers={"X-CSRF-Token": csrf}
    )
    assert up.status_code == 201 and up.json()["name"] == "grr"
    iid = up.json()["id"]
    assert (await client.get(f"/api/v1/cockpit/icons/{iid}")).content == PNG_1PX
    client.cookies.clear()
    await login(client, "bob")
    assert (await client.get(f"/api/v1/cockpit/icons/{iid}")).status_code == 404


def test_reconcile_adds_new_connection_once_and_purges_deleted() -> None:
    from mypds.cockpit.schema import reconcile
    from mypds.connectors.proxmox import demo
    from mypds.connectors.proxmox.connector import build_summary

    old, new = str(uuid.uuid4()), str(uuid.uuid4())
    data = build_summary(demo.cluster_status(), demo.cluster_resources())
    doc = default_layout([(old, data)]).dump()
    # La connexion « old » est supprimée, « new » est ajoutée
    doc, changed = reconcile(doc, {new}, {new: data})
    assert changed
    tiles = [t for g in doc["groups"] for r in g["rows"] for t in r["tiles"]]
    assert all(t["config"].get("connector_id") in (None, new) for t in tiles)
    assert sum(t["type"] == "proxmox.node" for t in tiles) == 2
    assert doc["known_connectors"] == [new]
    CockpitLayout.model_validate(doc)  # reste un document valide
    # Supprimer volontairement ses tuiles : elles ne reviennent pas
    for g in doc["groups"]:
        for r in g["rows"]:
            r["tiles"] = [t for t in r["tiles"] if t["config"].get("connector_id") != new]
    doc, changed = reconcile(doc, {new}, {new: data})
    assert not any(t["config"].get("connector_id") == new for g in doc["groups"] for r in g["rows"] for t in r["tiles"])


def test_reconcile_waits_for_first_snapshot() -> None:
    from mypds.cockpit.schema import reconcile

    cid = str(uuid.uuid4())
    doc, changed = reconcile(default_layout([]).dump(), {cid}, {cid: None})
    assert not changed and doc["known_connectors"] == []


def test_default_tabs_follow_the_interface_language() -> None:
    assert [g["title"] for g in default_layout([], "en").dump()["groups"]] == ["Home", "Infrastructure", "Services"]
    assert [g["title"] for g in default_layout([]).dump()["groups"]][0] == "Accueil"


def test_new_connection_lands_in_the_english_home_tab() -> None:
    from mypds.cockpit.schema import reconcile
    from mypds.connectors.proxmox import demo
    from mypds.connectors.proxmox.connector import build_summary

    cid = "22222222-2222-2222-2222-222222222222"
    data = build_summary(demo.cluster_status(), demo.cluster_resources())
    doc = default_layout([], "en").dump()
    doc["groups"][0]["id"] = "g_custom"  # identifiant modifié : retrouvé par son nom
    doc, changed = reconcile(doc, {cid}, {cid: data}, "en")
    assert changed
    home = doc["groups"][0]
    assert home["title"] == "Home" and any(t["config"].get("connector_id") == cid for t in home["rows"][0]["tiles"])
    assert [g["title"] for g in doc["groups"]].count("Infrastructure") == 1
