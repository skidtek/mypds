import pytest
from pydantic import ValidationError

from mypds.connectors.proxmox import demo
from mypds.connectors.proxmox.connector import ProxmoxConfig, ProxmoxConnector, ProxmoxSecrets, build_summary

GIB = 1024**3


def test_summary_from_demo_shape() -> None:
    s = build_summary(demo.cluster_status(), demo.cluster_resources())
    assert s["cluster"]["name"] == "demo-cluster" and s["cluster"]["quorate"] is True
    assert s["cluster"]["nodes_online"] == 2 and s["cluster"]["health"] == "ok"
    assert s["guests"] == {"vm_running": 1, "vm_stopped": 1, "lxc_running": 5, "lxc_stopped": 1}
    # Stockage partagé « nas » compté une seule fois
    assert s["resources"]["disk_total"] == 200 * GIB * 2 + 4000 * GIB
    assert {g["id"] for g in s["guest_list"]} >= {"qemu/100", "lxc/105"}


def test_standalone_node_and_offline() -> None:
    status = [{"type": "node", "name": "pve02", "online": 1, "ip": "192.0.2.62"}]
    resources = [
        {
            "type": "node",
            "node": "pve02",
            "status": "online",
            "cpu": 0.01,
            "maxcpu": 6,
            "mem": 4 * GIB,
            "maxmem": 8 * GIB,
        },
        {"type": "node", "node": "pve03", "status": "offline"},
        {"type": "lxc", "id": "lxc/200", "vmid": 200, "node": "pve02", "status": "running", "template": 1},
    ]
    s = build_summary(status, resources)
    assert s["cluster"]["standalone"] is True and s["cluster"]["name"] == "pve02"
    assert s["cluster"]["health"] == "warning"  # un nœud hors ligne
    assert s["guests"]["lxc_running"] == 0  # les modèles ne comptent pas
    assert s["resources"]["mem"] == 0.5


def test_config_validation() -> None:
    with pytest.raises(ValidationError):
        ProxmoxConfig.model_validate({"mode": "live"})  # hôte et jeton requis
    with pytest.raises(ValidationError):
        ProxmoxConfig.model_validate({"mode": "live", "host": "pve; rm -rf", "token_id": "mypds@pve!monitor"})
    with pytest.raises(ValidationError):
        ProxmoxConfig.model_validate({"mode": "live", "host": "192.0.2.62", "token_id": "root"})
    with pytest.raises(ValidationError):
        ProxmoxConfig.model_validate({"mode": "live", "host": "pve", "token_id": "a@pve!b", "tls_fingerprint": "zz"})
    ok = ProxmoxConfig.model_validate(
        {"mode": "live", "host": "192.0.2.62", "token_id": "mypds@pve!monitor", "tls_fingerprint": "AB:" * 31 + "AB"}
    )
    assert ok.tls_fingerprint == "ab" * 32


async def test_history_rejects_injection() -> None:
    from mypds.connectors.sdk import ConnectorError

    c = ProxmoxConnector("x", ProxmoxConfig(mode="demo"), ProxmoxSecrets())
    assert len(await c.history("node/pve01", "hour")) == 70
    assert await c.history("lxc/105@pve02", "day")
    for bad in ("node/../../access", "qemu/1@pve/../x", "node/pve01?x=1"):
        with pytest.raises(ConnectorError):
            await c.history(bad, "hour")
