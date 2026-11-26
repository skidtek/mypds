from mypds.alerts.rules import CpuHistory, proxmox_rules
from mypds.connectors.proxmox import demo
from mypds.connectors.proxmox.connector import build_summary, summarize_tasks
from tests.conftest import login

GIB = 1024**3


def demo_data(on_demand: set[str] | None = None) -> dict:
    d = build_summary(demo.cluster_status(), demo.cluster_resources())
    for g in d["guest_list"]:
        g["on_demand"] = g["id"] in (on_demand or set())
    d["tasks"] = summarize_tasks(demo.cluster_tasks(), {str(g["vmid"]): g["name"] for g in d["guest_list"]})
    return d


def keys(cands) -> set[str]:  # noqa: ANN001
    return {c.key for c in cands}


def test_stopped_guests_and_on_demand() -> None:
    k = keys(proxmox_rules(demo_data(), CpuHistory(), "c"))
    assert {"guest-stopped:qemu/110", "guest-stopped:lxc/120"} <= k
    k2 = keys(proxmox_rules(demo_data({"qemu/110"}), CpuHistory(), "c"))
    assert "guest-stopped:qemu/110" not in k2 and "guest-stopped:lxc/120" in k2


def test_failed_backup_only_latest_counts() -> None:
    d = demo_data()
    assert "backup:102" in keys(proxmox_rules(d, CpuHistory(), "c"))
    # Une sauvegarde réussie plus récente résout l'échec précédent
    newer = dict(d["tasks"][0], target="102", type="vzdump", state="ok", start=9e12, end=9e12 + 1, upid="new")
    d["tasks"] = [newer, *d["tasks"]]
    assert "backup:102" not in keys(proxmox_rules(d, CpuHistory(), "c"))


def test_thresholds_memory_storage_offline_quorum() -> None:
    d = demo_data()
    d["nodes"][0].update(mem=0.9 * d["nodes"][0]["maxmem"])
    d["nodes"][1].update(online=False)
    d["storages"] = [{"storage": "nas", "node": None, "shared": True, "used": 96, "total": 100}]
    d["cluster"]["quorate"] = False
    cands = {c.key: c for c in proxmox_rules(d, CpuHistory(), "c")}
    assert cands["mem:pve01"].severity == "warning"
    assert cands["node-offline:pve02"].severity == "critical"
    assert cands["storage:*:nas"].severity == "critical"
    assert cands["quorum"].severity == "critical"


def test_cpu_must_be_sustained_five_minutes() -> None:
    d = demo_data()
    d["nodes"][0]["cpu"] = 0.97
    hist = CpuHistory()
    assert "cpu:pve01" not in keys(proxmox_rules(d, hist, "c", now=1000))  # pic isolé
    for t in range(1015, 1330, 15):
        result = proxmox_rules(d, hist, "c", now=t)
    assert {c.key: c.severity for c in result}["cpu:pve01"] == "critical"
    d["nodes"][0]["cpu"] = 0.2  # une seule mesure basse suffit à lever l'alerte
    assert "cpu:pve01" not in keys(proxmox_rules(d, hist, "c", now=1345))


async def test_alert_lifecycle_and_on_demand_api(client) -> None:
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    r = await client.post(
        "/api/v1/connectors", json={"type": "proxmox", "name": "Démo", "config": {"mode": "demo"}}, headers=h
    )
    cid = r.json()["id"]
    active = (await client.get("/api/v1/alerts")).json()["active"]
    titles = {a["title"] for a in active}
    assert "VM windows-test (110) arrêté" in titles and all(a["demo"] for a in active)
    assert active[0]["severity"] in ("critical", "warning")
    # Option « Ignorer » : la VM démarrée à la demande ne lève plus d'alerte, l'alerte est résolue
    bob = await client.post(
        f"/api/v1/connectors/{cid}/on-demand", json={"guest": "qemu/110", "on_demand": True}, headers=h
    )
    assert bob.status_code == 200 and "qemu/110" in bob.json()["config"]["on_demand"]
    after = (await client.get("/api/v1/alerts")).json()
    assert "VM windows-test (110) arrêté" not in {a["title"] for a in after["active"]}
    assert "VM windows-test (110) arrêté" in {a["title"] for a in after["resolved"]}
    snap = next(s for s in (await client.get("/api/v1/connectors/snapshots")).json() if s["id"] == cid)
    assert next(g for g in snap["data"]["guest_list"] if g["id"] == "qemu/110")["on_demand"] is True
    assert snap["data"]["tasks"] and snap["data"]["tasks"][0]["label"]
    bad = await client.post(
        f"/api/v1/connectors/{cid}/on-demand", json={"guest": "qemu/1;x", "on_demand": True}, headers=h
    )
    assert bad.status_code == 422
    await client.delete(f"/api/v1/connectors/{cid}", headers=h)
    assert (await client.get("/api/v1/alerts")).json()["active"] == []


async def test_on_demand_admin_only(client) -> None:
    import uuid

    csrf = await login(client, "bob")
    r = await client.post(
        f"/api/v1/connectors/{uuid.uuid4()}/on-demand",
        json={"guest": "qemu/1", "on_demand": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 403


def test_custom_thresholds_and_cpu_duration() -> None:
    from mypds.alerts.settings import AlertSettings

    d = demo_data()
    d["nodes"][0].update(mem=0.78 * d["nodes"][0]["maxmem"], cpu=0.8)
    strict = AlertSettings(mem_warn=75, mem_crit=90, cpu_warn=75, cpu_crit=90, cpu_minutes=2)
    hist = CpuHistory()
    for t in range(1000, 1140, 15):
        result = {c.key: c for c in proxmox_rules(d, hist, "c", now=t, settings=strict)}
    assert result["mem:pve01"].severity == "warning"
    assert result["cpu:pve01"].params["minutes"] == 2  # 2 minutes suffisent avec ce réglage
    assert "mem:pve01" not in keys(proxmox_rules(d, CpuHistory(), "c", settings=AlertSettings()))


async def test_alert_settings_api(client) -> None:
    csrf = await login(client, "bob")
    assert (await client.get("/api/v1/alerts/settings")).json()["cpu_minutes"] == 5
    assert (await client.put("/api/v1/alerts/settings", json={}, headers={"X-CSRF-Token": csrf})).status_code == 403
    client.cookies.clear()
    csrf = await login(client)
    h = {"X-CSRF-Token": csrf}
    base = (await client.get("/api/v1/alerts/settings")).json()
    assert (
        await client.put("/api/v1/alerts/settings", json=base | {"cpu_warn": 96, "cpu_crit": 90}, headers=h)
    ).status_code == 422
    assert (await client.put("/api/v1/alerts/settings", json=base | {"mem_warn": 60}, headers=h)).status_code == 422
    ok = await client.put("/api/v1/alerts/settings", json=base | {"disk_warn": 80, "cpu_minutes": 10}, headers=h)
    assert ok.status_code == 200 and ok.json()["disk_warn"] == 80
    await client.put("/api/v1/alerts/settings", json=base, headers=h)
