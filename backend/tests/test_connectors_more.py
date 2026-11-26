"""UniFi, Synology et Docker : lecture des réponses, mode démo, règles d'alerte, tuiles par défaut."""

import pytest
from pydantic import ValidationError

from mypds.alerts.rules import docker_rules, synology_rules, unifi_rules
from mypds.cockpit.schema import CockpitLayout, default_layout, reconcile
from mypds.connectors.docker import demo as docker_demo
from mypds.connectors.docker.connector import DockerConfig, DockerConnector, DockerSecrets, cpu_pct
from mypds.connectors.sdk import ConnectorError, registry
from mypds.connectors.synology import connector as syno
from mypds.connectors.synology.connector import SynologyConfig, SynologyConnector, SynologySecrets
from mypds.connectors.unifi import demo as unifi_demo
from mypds.connectors.unifi.connector import UnifiConfig, UnifiConnector, UnifiSecrets, device_kind
from mypds.core import net


def test_registry_has_builtin_connectors() -> None:
    assert {"proxmox", "unifi", "synology", "docker"} <= set(registry())


# ---------- UniFi ----------
async def test_unifi_demo_and_rules() -> None:
    c = UnifiConnector("x", UnifiConfig(mode="demo"), UnifiSecrets())
    d = (await c.collect()).data
    assert d["gateway"]["model"] == "UDM-SE" and d["wan"]["down_bps"] > 0
    assert d["counts"] == {"devices": 4, "online": 3, "offline": 1, "updates": 1}
    assert d["clients"] == {"total": 33, "wired": 9, "wireless": 23, "vpn": 1}
    assert "speedtest" in d["unavailable"]
    alerts = unifi_rules(d)
    assert [(a.kind, a.severity, a.params["name"]) for a in alerts] == [("device-offline", "warning", "Wi-Fi étage")]
    d["devices"][0]["online"] = False  # passerelle
    assert any(a.severity == "critical" for a in unifi_rules(d))


async def test_unifi_live_parsing_tolerant(monkeypatch) -> None:
    c = UnifiConnector("x", UnifiConfig(host="192.168.1.1", site="Maison"), UnifiSecrets(api_key="k"))

    async def fake(self, path):
        if path == "/info":
            raise ConnectorError("absent")  # anciennes versions : pas de /info
        if "/statistics/latest" in path:
            return {}  # statistiques absentes
        return unifi_demo.api(path)

    monkeypatch.setattr(UnifiConnector, "_get", fake)
    d = (await c.collect()).data
    assert d["app_version"] is None and d["gateway"]["cpu_pct"] is None and d["site"]["name"] == "Maison"
    bad = UnifiConnector("x", UnifiConfig(host="h", site="Bureau"), UnifiSecrets(api_key="k"))
    with pytest.raises(ConnectorError, match="introuvable"):
        await bad.collect()


def test_unifi_kinds_and_config() -> None:
    assert device_kind({"model": "UDM-SE"}) == "gateway"
    # Network 11 : nom complet, et l'UDM ne déclare que « switching » (vu sur une UDM Pro SE réelle)
    assert device_kind({"model": "UniFi Dream Machine PRO SE", "features": ["switching"]}) == "gateway"
    assert device_kind({"model": "IW HD", "features": ["switching", "accessPoint"]}) == "ap"
    assert device_kind({"model": "USW Lite 16 PoE", "features": ["switching"]}) == "switch"
    assert device_kind({"model": "U7-Pro", "features": ["accessPoint"]}) == "ap"
    assert device_kind({"model": "USW-24", "features": ["switching"]}) == "switch"
    with pytest.raises(ValidationError):
        UnifiConfig(mode="live")


# ---------- Synology ----------
async def test_synology_demo_and_rules() -> None:
    c = SynologyConnector("x", SynologyConfig(mode="demo"), SynologySecrets())
    d = (await c.collect()).data
    assert d["model"] == "DS923+" and d["update_available"] is True and len(d["disks"]) == 4
    assert d["volumes"][0]["state"] == "normal" and d["volumes"][1]["state"] == "busy"
    kinds = sorted((a.kind, a.severity) for a in synology_rules(d))
    assert ("disk", "warning") in kinds  # disque 3 : santé « avertissement »
    assert ("backup", "warning") in kinds  # tâche Hyper Backup en échec
    assert ("volume-full", "critical") in kinds  # groupe de stockage à 99 %


async def test_synology_snmp_parsing(monkeypatch) -> None:
    async def fake_get(host, port, cred, oids):
        return dict.fromkeys(oids) | {"model": "DS220+", "version": "DSM 7.2", "status": 1, "upgrade": 2}

    async def fake_table(host, port, cred, oid):
        if oid == syno.DISK:
            return {"1": {5: 5, 6: 52, 12: "sata1"}}  # disque en panne
        return {"1": {2: "Volume 1", 3: 11, 4: 100, 5: 1000}}  # volume dégradé

    monkeypatch.setattr(syno.snmp, "get", fake_get)
    monkeypatch.setattr(syno.snmp, "table", fake_table)
    cfg = SynologyConfig(host="nas.lan", snmp_user="mypds")
    d = (
        await SynologyConnector("x", cfg, SynologySecrets(snmp_auth_key="a" * 8, snmp_priv_key="b" * 8)).collect()
    ).data
    assert d["update_available"] is False and d["disks"][0]["status"] == "crashed" and d["volumes"][0]["pct"] == 0.9
    assert {a.kind for a in synology_rules(d)} >= {"disk", "volume", "volume-full"}
    with pytest.raises(ValidationError):
        SynologyConfig(host="nas.lan")  # utilisateur SNMP requis
    with pytest.raises(ValidationError):
        SynologySecrets(snmp_auth_key="court")  # 8 caractères minimum (SNMP v3)


async def test_synology_without_keys() -> None:
    c = SynologyConnector("x", SynologyConfig(host="nas.lan", snmp_user="u"), SynologySecrets())
    with pytest.raises(ConnectorError, match="SNMP"):
        await c.collect()


# ---------- Docker ----------
async def test_docker_demo_and_rules() -> None:
    c = DockerConnector("x", DockerConfig(mode="demo", on_demand=["/uptime-kuma"]), DockerSecrets())
    d = (await c.collect()).data
    assert d["counts"]["running"] == 5 and d["counts"]["unhealthy"] == 1
    kuma = next(x for x in d["containers"] if x["name"] == "uptime-kuma")
    assert kuma["on_demand"] and kuma["exit_code"] == 1
    jelly = next(x for x in d["containers"] if x["name"] == "jellyfin")
    assert jelly["cpu_pct"] and jelly["mem_used"] and jelly["ports"] == ["8096→8096/tcp"]
    kinds = {a.kind for a in docker_rules(d)}
    assert kinds == {"container-unhealthy"}  # conteneur arrêté « à la demande » : pas d'alerte
    kuma["on_demand"] = False
    assert "container-stopped" in {a.kind for a in docker_rules(d)}


async def test_docker_needs_certificates_and_reads_only(monkeypatch) -> None:
    c = DockerConnector("x", DockerConfig(host="docker.lan"), DockerSecrets())
    with pytest.raises(ConnectorError, match="Certificats"):
        await c.collect()
    seen: list[str] = []

    async def fake_fetch(url, **kw):
        seen.append(url)
        assert "client_tls" in kw and "method" not in kw  # lecture seule (GET)
        raise net.OutboundError("Connexion impossible : refus")

    monkeypatch.setattr(net, "fetch", fake_fetch)
    c = DockerConnector("x", DockerConfig(host="docker.lan"), DockerSecrets(ca_pem="x", cert_pem="y", key_pem="z"))
    with pytest.raises(ConnectorError):
        await c.collect()
    assert seen == ["https://docker.lan:2376/v1.41/version"]


def test_client_tls_rejects_bad_pem() -> None:
    with pytest.raises(net.OutboundError, match="CA"):
        net.ClientTls("pas un certificat", "x", "y").context()


def test_cpu_formula() -> None:
    s = docker_demo.api("/containers/" + "b2c3d4e5f6a1" * 5 + "/stats")
    assert cpu_pct(s) == pytest.approx(22 * 400_000 / 40_000_000 * 4 * 100, rel=0.01)  # 88 % (4 cœurs)
    assert cpu_pct({}) is None


# ---------- Disposition ----------
def test_default_tiles_for_new_types() -> None:
    unifi = {"devices": [{"id": "d-gw"}, {"id": "d-ap"}]}
    docker = {"containers": [{"name": "jellyfin"}]}
    doc = default_layout(
        [
            ("11111111-1111-1111-1111-111111111111", unifi, "unifi"),
            ("22222222-2222-2222-2222-222222222222", docker, "docker"),
            ("33333333-3333-3333-3333-333333333333", {}, "synology"),
        ]
    ).dump()
    types = [t["type"] for g in doc["groups"] for r in g["rows"] for t in r["tiles"]]
    assert types.count("unifi.device") == 2 and "docker.container" in types and "synology.summary" in types
    doc, changed = reconcile(doc, {"11111111-1111-1111-1111-111111111111"}, {})
    assert changed and not any(
        "docker" in t for t in [t["type"] for g in doc["groups"] for r in g["rows"] for t in r["tiles"]]
    )
    CockpitLayout.model_validate(doc)


def test_host_pasted_as_url_is_accepted() -> None:
    assert UnifiConfig(host="https://192.168.0.1/").host == "192.168.0.1"
    c = UnifiConfig(host="https://udm.home.lan:8443/network")
    assert (c.host, c.port) == ("udm.home.lan", 8443)
    assert SynologyConfig(host="nas.lan:1161", snmp_user="u").snmp_port == 1161
    assert DockerConfig(host="tcp://docker.lan:2376").host == "docker.lan"


def test_readable_validation_errors() -> None:
    from mypds.connectors.sdk import readable

    with pytest.raises(ValidationError) as e:
        UnifiConfig(host="bad host!")
    assert readable(e.value) == "Adresse invalide : indiquez seulement l'IP ou le nom (ex. 192.168.0.1)"
    with pytest.raises(ValidationError) as e:
        UnifiConfig(mode="live")
    assert "Adresse de la console UniFi requise" in readable(e.value)


async def test_cli_demo_adds_one_demo_connector_per_missing_type(db_schema) -> None:
    from sqlalchemy import delete, select

    from mypds.cli import _demo
    from mypds.connectors.models import ConnectorInstance
    from mypds.connectors.sdk import registry
    from mypds.core.db import sessionmaker

    async with sessionmaker()() as db:
        before = set(await db.scalars(select(ConnectorInstance.id)))
    added = await _demo()
    try:
        assert set(added) <= set(registry())
        async with sessionmaker()() as db:
            rows = [r for r in await db.scalars(select(ConnectorInstance)) if r.id not in before]
        assert {r.type for r in rows} == set(added)
        assert all(r.config.get("mode") == "demo" and r.name.endswith("(demo)") for r in rows)
        assert await _demo() == []  # idempotent
    finally:
        async with sessionmaker()() as db:
            await db.execute(delete(ConnectorInstance).where(ConnectorInstance.id.not_in(before or {None})))
            await db.commit()
