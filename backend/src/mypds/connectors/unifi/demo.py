"""Données de démonstration UniFi (fictives, toujours signalées « Démo » à l'écran)."""

from __future__ import annotations

import math
import time
from typing import Any

SITE = {"id": "demo-site", "internalReference": "default", "name": "Maison"}
DEVICES = [
    {
        "id": "d-gw",
        "name": "Passerelle",
        "model": "UDM-SE",
        "state": "ONLINE",
        "ipAddress": "192.168.1.1",
        "features": ["switching"],
        "firmwareVersion": "4.1.13",
        "firmwareUpdatable": False,
    },
    {
        "id": "d-sw",
        "name": "Switch bureau",
        "model": "USW-Lite-16-PoE",
        "state": "ONLINE",
        "ipAddress": "192.168.1.2",
        "features": ["switching"],
        "firmwareVersion": "7.1.26",
        "firmwareUpdatable": True,
    },
    {
        "id": "d-ap1",
        "name": "Wi-Fi salon",
        "model": "U7-Pro",
        "state": "ONLINE",
        "ipAddress": "192.168.1.10",
        "features": ["accessPoint"],
        "firmwareVersion": "8.0.24",
        "firmwareUpdatable": False,
    },
    {
        "id": "d-ap2",
        "name": "Wi-Fi étage",
        "model": "U6-Lite",
        "state": "OFFLINE",
        "ipAddress": "192.168.1.11",
        "features": ["accessPoint"],
        "firmwareVersion": "6.6.77",
        "firmwareUpdatable": False,
    },
]


def _stats(dev_id: str) -> dict[str, Any]:
    t = time.time() / 30
    if dev_id == "d-ap2":
        return {}
    base = {"d-gw": (38e6, 6e6), "d-sw": (12e6, 3e6), "d-ap1": (9e6, 2e6)}[dev_id]
    wave = 1 + 0.35 * math.sin(t)
    return {
        "uptimeSec": 86400 * 12 + int(time.time()) % 86400,
        "cpuUtilizationPct": {"d-gw": 14.0, "d-sw": 6.0, "d-ap1": 9.0}[dev_id],
        "memoryUtilizationPct": {"d-gw": 48.0, "d-sw": 31.0, "d-ap1": 40.0}[dev_id],
        "uplink": {"rxRateBps": int(base[0] * wave), "txRateBps": int(base[1] * wave)},
    }


def api(path: str) -> Any:
    if path == "/info":
        return {"applicationVersion": "9.4.19"}
    if path.startswith("/sites?"):
        return {"data": [SITE]}
    if path.endswith("/devices?limit=200"):
        return {"data": DEVICES}
    if path.endswith("/statistics/latest"):
        return _stats(path.split("/")[-3])
    if "/devices/" in path:
        return next(d for d in DEVICES if d["id"] == path.split("/")[-1])
    if "/clients" in path:
        return {"data": [{"type": "WIRELESS"}] * 23 + [{"type": "WIRED"}] * 9 + [{"type": "VPN"}]}
    return {}
