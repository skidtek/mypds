"""Données de démonstration Docker (fictives, toujours signalées « Démo » à l'écran)."""

from __future__ import annotations

import time
from typing import Any

_C = [
    (
        "a1b2c3d4e5f6",
        "homeassistant",
        "ghcr.io/home-assistant/home-assistant:stable",
        "running",
        "healthy",
        "domotique",
        8123,
    ),
    ("b2c3d4e5f6a1", "jellyfin", "jellyfin/jellyfin:latest", "running", None, "media", 8096),
    ("c3d4e5f6a1b2", "nextcloud", "nextcloud:29-apache", "running", "unhealthy", "cloud", 8080),
    ("d4e5f6a1b2c3", "nextcloud-db", "postgres:16", "running", "healthy", "cloud", None),
    ("e5f6a1b2c3d4", "uptime-kuma", "louislam/uptime-kuma:1", "exited", None, None, 3001),
    ("f6a1b2c3d4e5", "vaultwarden", "vaultwarden/server:latest", "running", "healthy", None, 8081),
]


def api(path: str) -> Any:
    if path == "/version":
        return {"Version": "27.3.1", "ApiVersion": "1.47"}
    if path == "/info":
        return {
            "Name": "docker-demo",
            "OperatingSystem": "Debian GNU/Linux 13 (trixie)",
            "NCPU": 4,
            "MemTotal": 8 * 1024**3,
            "Images": 14,
        }
    if path.startswith("/containers/json"):
        return [
            {
                "Id": i * 5,
                "Names": [f"/{n}"],
                "Image": img,
                "State": st,
                "Status": "Up 3 days" if st == "running" else "Exited (1) 2 hours ago",
                "Labels": {"com.docker.compose.project": proj} if proj else {},
                "Ports": [{"PublicPort": port, "PrivatePort": port, "Type": "tcp"}] if port else [],
            }
            for i, n, img, st, _h, proj, port in _C
        ]
    cid = path.split("/")[2]
    c = next(x for x in _C if x[0] * 5 == cid)
    if path.endswith("/json"):
        return {
            "RestartCount": 3 if c[1] == "nextcloud" else 0,
            "State": {
                "ExitCode": 1 if c[3] == "exited" else 0,
                "StartedAt": "2026-11-22T08:00:00Z",
                **({"Health": {"Status": c[4]}} if c[4] else {}),
            },
        }
    t = int(time.time())
    load = {"homeassistant": 6, "jellyfin": 22, "nextcloud": 3, "nextcloud-db": 2, "vaultwarden": 1}.get(c[1], 1)
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 10_000_000 + load * 400_000 + t % 7},
            "system_cpu_usage": 100_000_000,
            "online_cpus": 4,
        },
        "precpu_stats": {"cpu_usage": {"total_usage": 10_000_000}, "system_cpu_usage": 60_000_000},
        "memory_stats": {"usage": load * 60 * 1024**2, "limit": 8 * 1024**3, "stats": {"inactive_file": 0}},
    }
