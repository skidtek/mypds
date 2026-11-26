"""Règles d'alerte Proxmox (fonctions pures, testables).

Seuils réglables (`AlertSettings`, par défaut 85 % / 95 %). Le CPU doit rester au-dessus du seuil
pendant la durée choisie (par défaut 5 minutes, pics brefs ignorés). Un invité arrêté est une anomalie,
sauf s'il est marqué « démarré à la demande ».
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

TASK_WINDOW_S = 86400
MAX_SUSTAIN_S = 1800


@dataclass(slots=True)
class Candidate:
    key: str
    kind: str
    severity: str
    title: str
    detail: str | None = None
    resource: str | None = None
    # Paramètres du message : l'interface compose le texte dans la langue de l'utilisateur
    params: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


def _level(v: float | None, warn: int, crit: int) -> str | None:
    """`warn` et `crit` en pourcentage (réglages utilisateur)."""
    if v is None:
        return None
    return "critical" if v * 100 >= crit else "warning" if v * 100 >= warn else None


def _pct(v: float) -> str:
    return f"{round(v * 100)} %"


class CpuHistory:
    """Échantillons CPU récents par nœud, pour n'alerter que sur une charge soutenue."""

    def __init__(self) -> None:
        self._s: dict[str, deque[tuple[float, float]]] = {}

    def add(self, key: str, value: float, now: float) -> None:
        q = self._s.setdefault(key, deque())
        q.append((now, value))
        while q and q[0][0] < now - MAX_SUSTAIN_S - 120:
            q.popleft()

    def sustained(self, key: str, now: float, seconds: float = 300) -> float | None:
        """Charge minimale sur la période demandée, si elle est entièrement couverte par des mesures."""
        q = self._s.get(key)
        if not q or q[0][0] > now - seconds:
            return None
        return min(v for t, v in q if t >= now - seconds - 60)


def proxmox_rules(
    data: dict[str, Any], cpu: CpuHistory, prefix: str, now: float | None = None, settings: Any = None
) -> list[Candidate]:
    from mypds.alerts.settings import AlertSettings

    st_: AlertSettings = settings or AlertSettings()
    now = time.time() if now is None else now
    out: list[Candidate] = []
    c = data["cluster"]
    if c.get("quorate") is False:
        out.append(
            Candidate(
                "quorum",
                "quorum",
                "critical",
                f"Quorum perdu sur le cluster {c.get('name')}",
                "Le cluster ne peut plus prendre de décision : vérifiez les nœuds et le réseau.",
                params={"cluster": c.get("name")},
            )
        )
    for n in data["nodes"]:
        name = n["name"]
        if not n["online"]:
            out.append(
                Candidate(
                    f"node-offline:{name}",
                    "node-offline",
                    "critical",
                    f"Nœud {name} hors ligne",
                    resource=f"node/{name}",
                    params={"node": name},
                )
            )
            continue
        if n.get("cpu") is not None:
            cpu.add(f"{prefix}:{name}", n["cpu"], now)
            sustained = cpu.sustained(f"{prefix}:{name}", now, st_.cpu_minutes * 60)
            if (lvl := _level(sustained, st_.cpu_warn, st_.cpu_crit)) and sustained is not None:
                out.append(
                    Candidate(
                        f"cpu:{name}",
                        "cpu",
                        lvl,
                        f"CPU élevé sur {name}",
                        f"Au moins {_pct(sustained)} depuis {st_.cpu_minutes} minutes",
                        f"node/{name}",
                        params={"node": name, "pct": round(sustained * 100), "minutes": st_.cpu_minutes},
                    )
                )
        if n.get("maxmem"):
            ratio = (n.get("mem") or 0) / n["maxmem"]
            if lvl := _level(ratio, st_.mem_warn, st_.mem_crit):
                out.append(
                    Candidate(
                        f"mem:{name}",
                        "memory",
                        lvl,
                        f"Mémoire presque pleine sur {name}",
                        _pct(ratio),
                        f"node/{name}",
                        params={"node": name, "pct": round(ratio * 100)},
                    )
                )
    for st in data.get("storages", []):
        if st.get("total"):
            ratio = st["used"] / st["total"]
            if lvl := _level(ratio, st_.disk_warn, st_.disk_crit):
                where = "partagé" if st.get("shared") else f"sur {st.get('node')}"
                out.append(
                    Candidate(
                        f"storage:{st.get('node') or '*'}:{st['storage']}",
                        "storage",
                        lvl,
                        f"Stockage {st['storage']} ({where}) presque plein",
                        _pct(ratio),
                        params={"storage": st["storage"], "node": st.get("node"), "pct": round(ratio * 100)},
                    )
                )
    for g in data["guest_list"]:
        if g["status"] != "running" and not g.get("on_demand"):
            kind = "VM" if g["type"] == "qemu" else "LXC"
            out.append(
                Candidate(
                    f"guest-stopped:{g['id']}",
                    "guest-stopped",
                    "warning",
                    f"{kind} {g['name']} ({g['vmid']}) arrêté",
                    f"Sur {g['node']}",
                    g["id"],
                    params={"type": g["type"], "name": g["name"], "vmid": g["vmid"], "node": g["node"]},
                )
            )
    # Sauvegardes : seule la plus récente de chaque invité compte
    latest_backup: dict[str, dict[str, Any]] = {}
    for t in data.get("tasks", []):
        if t["type"] == "vzdump" and t.get("end") and t["target"] not in latest_backup:
            latest_backup[t["target"]] = t
    for target, t in latest_backup.items():
        if t["state"] == "error":
            who = t.get("target_name") or target
            out.append(
                Candidate(
                    f"backup:{target}",
                    "backup",
                    "warning",
                    f"Sauvegarde de {who} en échec",
                    str(t.get("status"))[:200],
                    params={"name": who},
                )
            )
    for t in data.get("tasks", []):
        if t["type"] != "vzdump" and t["state"] == "error" and (t.get("end") or 0) >= now - TASK_WINDOW_S:
            who = t.get("target_name") or t.get("target") or t.get("node")
            out.append(
                Candidate(
                    f"task:{t['upid']}",
                    "task",
                    "warning",
                    f"{t['label']} en échec ({who})",
                    str(t.get("status"))[:200],
                    params={"task": t["type"], "who": who},
                )
            )
    return out


def unifi_rules(data: dict[str, Any]) -> list[Candidate]:
    """Équipement UniFi hors ligne : critique pour la passerelle (accès Internet), sinon avertissement."""
    out: list[Candidate] = []
    for d in data.get("devices", []):
        if d.get("online") is False:
            gw = d.get("kind") == "gateway"
            out.append(
                Candidate(
                    f"unifi-offline:{d['id']}",
                    "device-offline",
                    "critical" if gw else "warning",
                    f"{d['name']} hors ligne",
                    d.get("model"),
                    params={"name": d["name"], "model": d.get("model"), "gateway": gw},
                )
            )
    return out


def synology_rules(data: dict[str, Any], settings: Any = None) -> list[Candidate]:
    from mypds.alerts.settings import AlertSettings

    st_: AlertSettings = settings or AlertSettings()
    out: list[Candidate] = []
    for part, key in (("system", "system_ok"), ("power", "power_ok"), ("fans", "fans_ok"), ("thermal", "thermal_ok")):
        if data.get(key) is False:
            out.append(
                Candidate(
                    f"nas:{part}", "nas-hardware", "critical", f"Synology : anomalie {part}", params={"part": part}
                )
            )
    for d in data.get("disks", []):
        bad = d.get("status") in {"crashed", "partition_failed", "disconnected"} or d.get("health") in {
            "critical",
            "failing",
        }
        warn = d.get("health") == "warning"
        if bad or warn:
            state = d.get("health") if d.get("health") not in {None, "normal"} else d.get("status")
            out.append(
                Candidate(
                    f"disk:{d['id']}",
                    "disk",
                    "critical" if bad else "warning",
                    f"Disque {d['name']} : {state}",
                    d.get("model"),
                    params={"name": d["name"], "state": state},
                )
            )
    for v in data.get("volumes", []):
        if v.get("state") in {"degraded", "crashed"}:
            out.append(
                Candidate(
                    f"volume:{v['id']}",
                    "volume",
                    "critical",
                    f"{v['name']} : {v['state']}",
                    params={"name": v["name"], "state": v["state"]},
                )
            )
        if (lvl := _level(v.get("pct"), st_.disk_warn, st_.disk_crit)) and v.get("pct") is not None:
            out.append(
                Candidate(
                    f"volume-full:{v['id']}",
                    "volume-full",
                    lvl,
                    f"{v['name']} presque plein",
                    _pct(v["pct"]),
                    params={"name": v["name"], "pct": round(v["pct"] * 100)},
                )
            )
    backups = data.get("backups") or {}
    for t in backups.get("tasks", []) if backups.get("available") else []:
        if t.get("ok") is False:
            out.append(
                Candidate(
                    f"hyperbackup:{t['name']}",
                    "backup",
                    "warning",
                    f"Sauvegarde de {t['name']} en échec",
                    t.get("last_result"),
                    params={"name": t["name"]},
                )
            )
    return out


def docker_rules(data: dict[str, Any]) -> list[Candidate]:
    out: list[Candidate] = []
    for c in data.get("containers", []):
        name = c["name"]
        if c.get("state") in {"exited", "dead"} and not c.get("on_demand"):
            out.append(
                Candidate(
                    f"container-stopped:{name}",
                    "container-stopped",
                    "warning",
                    f"Conteneur {name} arrêté",
                    c.get("status"),
                    params={"name": name, "code": c.get("exit_code")},
                )
            )
        elif c.get("health") == "unhealthy":
            out.append(
                Candidate(
                    f"container-unhealthy:{name}",
                    "container-unhealthy",
                    "warning",
                    f"Conteneur {name} en mauvaise santé",
                    params={"name": name},
                )
            )
        elif c.get("state") == "restarting":
            out.append(
                Candidate(
                    f"container-restarting:{name}",
                    "container-restarting",
                    "warning",
                    f"Conteneur {name} redémarre en boucle",
                    params={"name": name, "count": c.get("restart_count")},
                )
            )
    return out
