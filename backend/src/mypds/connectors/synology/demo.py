"""Données de démonstration Synology (fictives, toujours signalées « Démo » à l'écran)."""

from __future__ import annotations

from typing import Any

TB = 1000**4


def snapshot() -> dict[str, Any]:
    from mypds.connectors.synology.connector import build  # import local : évite un import circulaire

    system = {
        "status": 1,
        "temperature": 41,
        "power": 1,
        "system_fan": 1,
        "cpu_fan": 1,
        "model": "DS923+",
        "version": "DSM 7.2.2-72806 Update 3",
        "upgrade": 1,
        "cpu_pct": 7,
        "mem_pct": 38,
        "thermal": 1,
    }
    disks = {
        str(i): {
            2: f"Disk {i}",
            3: "ST8000VN004",
            4: "SATA",
            5: 1,
            6: 34 + i,
            7: "data",
            9: 0,
            11: None,
            12: f"sata{i}",
            13: 2 if i == 3 else 1,
        }
        for i in range(1, 5)
    }
    raids = {
        "1": {2: "Volume 1", 3: 1, 4: int(9.1 * TB), 5: int(21.3 * TB)},
        "2": {2: "Storage Pool 1", 3: 13, 4: int(0.2 * TB), 5: int(21.8 * TB)},
    }
    data = build(system, disks, raids)
    data["backups"] = {
        "available": True,
        "tasks": [
            {
                "name": "Photos → C2",
                "state": "idle",
                "last_result": "done",
                "ok": True,
                "last_time": "2026-11-25 03:00",
                "next_time": "2026-11-26 03:00",
            },
            {
                "name": "Documents → USB",
                "state": "idle",
                "last_result": "failed",
                "ok": False,
                "last_time": "2026-11-24 23:30",
                "next_time": "2026-11-25 23:30",
            },
        ],
    }
    data["url"] = None
    return data
