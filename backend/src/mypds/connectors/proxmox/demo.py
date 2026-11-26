"""Données de DÉMONSTRATION au format de l'API Proxmox VE.

Fictives, clairement signalées à l'écran (badge « Démo »). Elles suivent la forme exacte des
réponses de /cluster/status, /cluster/resources et rrddata, pour exercer le même code que le
mode réel. Légère variation dans le temps pour rendre la démonstration vivante.
"""

from __future__ import annotations

import math
import time
from typing import Any

GIB = 1024**3
NODES = [
    {"name": "pve01", "ip": "192.0.2.11", "maxcpu": 8, "maxmem": 32 * GIB, "maxdisk": 100 * GIB, "base_cpu": 0.18},
    {"name": "pve02", "ip": "192.0.2.12", "maxcpu": 6, "maxmem": 16 * GIB, "maxdisk": 100 * GIB, "base_cpu": 0.09},
]
GUESTS = [
    ("qemu", 100, "home-assistant", "pve01", "running", 2, 4, "domotique"),
    ("lxc", 101, "docker", "pve01", "running", 4, 8, "services"),
    ("lxc", 102, "paperless", "pve01", "running", 2, 2, "services"),
    ("lxc", 103, "nginx-proxy", "pve02", "running", 1, 1, "reseau"),
    ("lxc", 104, "grr", "pve02", "running", 1, 1, "services"),
    ("lxc", 105, "mypds", "pve02", "running", 2, 2, ""),
    ("qemu", 110, "windows-test", "pve02", "stopped", 4, 8, "lab"),
    ("lxc", 120, "backup", "pve01", "stopped", 1, 1, ""),
]


def _wave(seed: float, base: float, amp: float, t: float | None = None) -> float:
    t = time.time() if t is None else t
    return max(0.0, base + amp * math.sin(t / 97 + seed) + amp * 0.4 * math.sin(t / 23 + seed * 2))


def cluster_status() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        {"type": "cluster", "name": "demo-cluster", "quorate": 1, "nodes": len(NODES), "version": 4}
    ]
    for i, n in enumerate(NODES, 1):
        out.append({"type": "node", "name": n["name"], "online": 1, "ip": n["ip"], "nodeid": i, "local": int(i == 1)})
    return out


def cluster_resources() -> list[dict[str, Any]]:
    res: list[dict[str, Any]] = []
    for i, n in enumerate(NODES):
        res.append(
            {
                "type": "node",
                "id": f"node/{n['name']}",
                "node": n["name"],
                "status": "online",
                "cpu": round(_wave(i, n["base_cpu"], 0.05), 4),
                "maxcpu": n["maxcpu"],
                "mem": int(n["maxmem"] * _wave(i + 3, 0.48, 0.04)),
                "maxmem": n["maxmem"],
                "disk": int(n["maxdisk"] * 0.31),
                "maxdisk": n["maxdisk"],
                "uptime": 86400 * (12 + i * 5),
            }
        )
        res.append(
            {
                "type": "storage",
                "id": f"storage/{n['name']}/local-lvm",
                "storage": "local-lvm",
                "node": n["name"],
                "status": "available",
                "shared": 0,
                "disk": int(200 * GIB * (0.35 + i * 0.1)),
                "maxdisk": 200 * GIB,
            }
        )
        res.append(
            {
                "type": "storage",
                "id": f"storage/{n['name']}/nas",
                "storage": "nas",
                "node": n["name"],
                "status": "available",
                "shared": 1,
                "disk": int(4000 * GIB * 0.62),
                "maxdisk": 4000 * GIB,
            }
        )
    for kind, vmid, name, node, status, cpus, mem_g, tags in GUESTS:
        running = status == "running"
        res.append(
            {
                "type": kind,
                "id": f"{kind}/{vmid}",
                "vmid": vmid,
                "name": name,
                "node": node,
                "status": status,
                "cpu": round(_wave(vmid, 0.06, 0.03), 4) if running else 0,
                "maxcpu": cpus,
                "mem": int(mem_g * GIB * _wave(vmid + 1, 0.45, 0.05)) if running else 0,
                "maxmem": mem_g * GIB,
                "uptime": 86400 * 3 + vmid * 3600 if running else 0,
                "tags": tags,
                "template": 0,
            }
        )
    return res


def rrd(seed: int, maxcpu: int, timeframe: str) -> list[dict[str, Any]]:
    step = {"hour": 60, "day": 1800, "week": 10800, "month": 43200, "year": 604800}[timeframe]
    now = int(time.time()) // step * step
    return [
        {
            "time": now - (69 - k) * step,
            "cpu": round(_wave(seed, 0.15, 0.08, now - (69 - k) * step), 4),
            "maxcpu": maxcpu,
            "memused": 0.5 * 16 * GIB * (1 + 0.1 * math.sin(k / 7 + seed)),
            "memtotal": 16 * GIB,
            "netin": 40000 + 20000 * math.sin(k / 5 + seed),
            "netout": 25000 + 15000 * math.cos(k / 6 + seed),
        }
        for k in range(70)
    ]


def cluster_tasks() -> list[dict[str, Any]]:
    """Activité fictive : sauvegardes nocturnes, démarrages, une sauvegarde en échec."""
    now = int(time.time())
    day = now - now % 86400
    tasks: list[dict[str, Any]] = []
    for k, (_kind, vmid, _name, node, *_rest) in enumerate(GUESTS[:6]):
        start = day - 86400 + 3 * 3600 + k * 420
        status = "OK" if vmid != 102 else "job errors"
        tasks.append(
            {
                "upid": f"UPID:{node}:demo{k}:vzdump",
                "node": node,
                "type": "vzdump",
                "id": str(vmid),
                "user": "root@pam",
                "starttime": start,
                "endtime": start + 300,
                "status": status,
            }
        )
    tasks.append(
        {
            "upid": "UPID:pve01:demo-start",
            "node": "pve01",
            "type": "qmstart",
            "id": "100",
            "user": "root@pam",
            "starttime": now - 2700,
            "endtime": now - 2690,
            "status": "OK",
        }
    )
    tasks.append(
        {
            "upid": "UPID:pve02:demo-stop",
            "node": "pve02",
            "type": "qmshutdown",
            "id": "110",
            "user": "root@pam",
            "starttime": now - 5400,
            "endtime": now - 5370,
            "status": "OK",
        }
    )
    tasks.append(
        {
            "upid": "UPID:pve01:demo-apt",
            "node": "pve01",
            "type": "aptupdate",
            "id": "",
            "user": "root@pam",
            "starttime": now - 720,
            "endtime": now - 700,
            "status": "OK",
        }
    )
    return tasks


def api(path: str) -> Any:
    base, _, query = path.partition("?")
    if base == "/version":
        return {"version": "9.2-démo", "release": "9.2"}
    if base == "/cluster/status":
        return cluster_status()
    if base == "/cluster/resources":
        return cluster_resources()
    if base == "/cluster/tasks":
        return cluster_tasks()
    if base.endswith("/rrddata"):
        timeframe = dict(p.split("=") for p in query.split("&") if "=" in p).get("timeframe", "hour")
        return rrd(len(base), 8, timeframe)
    return []
