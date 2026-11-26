"""Modèle de disposition du Digital Cockpit (mypds.cockpit-layout, version 1).

Hiérarchie stricte Groupe > Ligne > Tuile, conservée sur toutes les tailles d'écran : sur mobile,
les tuiles d'une ligne s'empilent sans quitter leur ligne ni leur groupe. Un groupe = un onglet.
Aucun secret : les tuiles référencent un connecteur par son identifiant.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA = "mypds.cockpit-layout"
CURRENT_VERSION = 1
Id = Annotated[str, Field(pattern=r"^[grt]_[A-Za-z0-9_-]{1,40}$")]
GUEST_RE = r"^(qemu|lxc)/\d{1,9}$"
NODE_RE = r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IconRef(Strict):
    kind: Literal["simple", "upload"]
    value: str = Field(pattern=r"^[a-z0-9-]{1,64}$|^[0-9a-f-]{36}$")


def _http_url(v: str | None) -> str | None:
    if v in (None, ""):
        return None
    if not v.lower().startswith(("https://", "http://")) or len(v) > 500:
        raise ValueError("L'adresse doit commencer par http:// ou https://")
    return v


class ProxmoxSummaryCfg(Strict):
    connector_id: uuid.UUID


class ProxmoxNodeCfg(Strict):
    connector_id: uuid.UUID
    node: str = Field(pattern=NODE_RE)


class ProxmoxGuestCfg(Strict):
    connector_id: uuid.UUID
    guest: str = Field(pattern=GUEST_RE)
    label: str | None = Field(default=None, max_length=60)
    icon: IconRef | None = None
    url: str | None = None

    _u = field_validator("url")(_http_url)


class ConnectorCfg(Strict):
    """Tuile résumé d'une connexion (UniFi, Synology, Docker)."""

    connector_id: uuid.UUID


class UnifiDeviceCfg(Strict):
    connector_id: uuid.UUID
    device: str = Field(pattern=r"^[A-Za-z0-9:_-]{1,64}$")
    label: str | None = Field(default=None, max_length=60)


class DockerContainerCfg(Strict):
    connector_id: uuid.UUID
    container: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")  # nom du conteneur (stable)
    label: str | None = Field(default=None, max_length=60)
    icon: IconRef | None = None
    url: str | None = None

    _u = field_validator("url")(_http_url)


class LinkCfg(Strict):
    label: str = Field(min_length=1, max_length=60)
    url: str
    icon: IconRef | None = None

    _u = field_validator("url")(_http_url)


class EmptyCfg(Strict):
    pass


TILE_CONFIGS: dict[str, type[Strict]] = {
    "alerts": EmptyCfg,
    "activity": EmptyCfg,
    "proxmox.summary": ProxmoxSummaryCfg,
    "proxmox.node": ProxmoxNodeCfg,
    "proxmox.guest": ProxmoxGuestCfg,
    "unifi.summary": ConnectorCfg,
    "unifi.device": UnifiDeviceCfg,
    "synology.summary": ConnectorCfg,
    "docker.summary": ConnectorCfg,
    "docker.container": DockerContainerCfg,
    "link": LinkCfg,
}
TileType = Literal[
    "proxmox.summary",
    "proxmox.node",
    "proxmox.guest",
    "unifi.summary",
    "unifi.device",
    "synology.summary",
    "docker.summary",
    "docker.container",
    "link",
    "alerts",
    "activity",
]


class Width(Strict):
    desktop: int = Field(default=4, ge=1, le=12)


class Tile(Strict):
    id: Id
    type: TileType
    width: Width = Field(default_factory=Width)
    config: dict[str, Any]

    @model_validator(mode="after")
    def _cfg(self) -> Tile:
        self.config = TILE_CONFIGS[self.type].model_validate(self.config).model_dump(mode="json", exclude_none=True)
        return self


class Row(Strict):
    id: Id
    title: str | None = Field(default=None, max_length=60)
    tiles: list[Tile] = Field(default_factory=list, max_length=24)


class Group(Strict):
    id: Id
    title: str = Field(min_length=1, max_length=40)
    icon: str | None = Field(default=None, pattern=r"^[a-z-]{1,30}$")
    rows: list[Row] = Field(default_factory=list, max_length=20)


class CockpitLayout(Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["mypds.cockpit-layout"] = Field(default=SCHEMA, alias="schema")
    version: Literal[1] = 1
    groups: list[Group] = Field(default_factory=list, min_length=1, max_length=30)
    # Connexions déjà intégrées à cette disposition : une nouvelle connexion y ajoute ses tuiles
    # une seule fois (si l'utilisateur les supprime ensuite, elles ne reviennent pas).
    known_connectors: list[uuid.UUID] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def _ids(self) -> CockpitLayout:
        ids: list[str] = []
        total = 0
        for g in self.groups:
            ids.append(g.id)
            for r in g.rows:
                ids.append(r.id)
                for t in r.tiles:
                    ids.append(t.id)
                    total += 1
        if len(ids) != len(set(ids)):
            raise ValueError("Identifiants en double dans la disposition")
        if total > 500:
            raise ValueError("Trop de tuiles (500 maximum)")
        return self

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("version") == CURRENT_VERSION:
        return document
    raise ValueError(f"Version de disposition non prise en charge : {document.get('version')}")


Conn = tuple[str, dict[str, Any] | None] | tuple[str, dict[str, Any] | None, str]


def _split(c: Conn) -> tuple[str, dict[str, Any] | None, str]:
    return (c[0], c[1], c[2]) if len(c) == 3 else (c[0], c[1], "proxmox")  # type: ignore[misc]


def tiles_for(ctype: str, cid: str, data: dict[str, Any] | None, tid: Any) -> dict[str, list[dict[str, Any]]]:
    """Tuiles proposées pour une connexion : résumé dans Accueil, équipements dans Infrastructure,
    services (VM, LXC, conteneurs) dans Services."""

    def tile(t: str, w: int, **cfg: Any) -> dict[str, Any]:
        return {"id": tid(), "type": t, "width": {"desktop": w}, "config": {"connector_id": cid, **cfg}}

    out: dict[str, list[dict[str, Any]]] = {"home": [], "infra": [], "services": []}
    data = data or {}
    if ctype == "proxmox":
        out["home"].append(tile("proxmox.summary", 12))
        out["infra"] = [tile("proxmox.node", 4, node=n["name"]) for n in data.get("nodes", [])[:12]]
        out["services"] = [tile("proxmox.guest", 3, guest=g["id"]) for g in data.get("guest_list", [])[:24]]
    elif ctype == "unifi":
        out["home"].append(tile("unifi.summary", 12))
        out["infra"] = [tile("unifi.device", 3, device=d["id"]) for d in data.get("devices", [])[:12]]
    elif ctype == "synology":
        out["home"].append(tile("synology.summary", 12))
    elif ctype == "docker":
        out["home"].append(tile("docker.summary", 12))
        out["services"] = [tile("docker.container", 3, container=c["name"]) for c in data.get("containers", [])[:24]]
    return out


# Noms des onglets créés par défaut, dans la langue de l'interface au moment de la création
GROUP_TITLES = {
    "fr": {"g_home": "Accueil", "g_infra": "Infrastructure", "g_services": "Services"},
    "en": {"g_home": "Home", "g_infra": "Infrastructure", "g_services": "Services"},
}


def _titles(lang: str) -> dict[str, str]:
    return GROUP_TITLES.get(lang, GROUP_TITLES["fr"])


def default_layout(conns: list[Conn], lang: str = "fr") -> CockpitLayout:
    """Onglets Accueil, Infrastructure, Services (selon la langue), pré-remplis avec les connexions existantes."""
    titles = _titles(lang)
    n = iter(range(1, 10_000))

    def tid() -> str:
        return f"t_{next(n)}"

    home: list[dict[str, Any]] = []
    infra: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    for c in conns:
        cid, data, ctype = _split(c)
        t = tiles_for(ctype, cid, data, tid)
        home.extend(t["home"])
        if data:
            infra.extend(t["infra"])
            services.extend(t["services"])
    groups = [
        {
            "id": "g_home",
            "title": titles["g_home"],
            "icon": "house",
            "rows": [
                {"id": "r_home", "tiles": home},
                {
                    "id": "r_home_feed",
                    "tiles": [
                        {"id": tid(), "type": "activity", "width": {"desktop": 6}, "config": {}},
                        {"id": tid(), "type": "alerts", "width": {"desktop": 6}, "config": {}},
                    ],
                },
            ],
        },
        {
            "id": "g_infra",
            "title": titles["g_infra"],
            "icon": "hard-drives",
            "rows": [{"id": "r_infra", "tiles": infra}],
        },
        {
            "id": "g_services",
            "title": titles["g_services"],
            "icon": "squares-four",
            "rows": [{"id": "r_services", "tiles": services}],
        },
    ]
    known = [_split(c)[0] for c in conns if _split(c)[1] is not None]
    return CockpitLayout.model_validate({"schema": SCHEMA, "version": 1, "groups": groups, "known_connectors": known})


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _group(doc: dict[str, Any], gid: str, icon: str, lang: str) -> dict[str, Any]:
    """Onglet par défaut `gid` : retrouvé par identifiant ou par nom (dans l'une des langues), sinon créé."""
    names = {t[gid].lower() for t in GROUP_TITLES.values()}
    title = _titles(lang)[gid]
    for g in doc["groups"]:
        if g["id"] == gid or g["title"].strip().lower() in names:
            if not g["rows"]:
                g["rows"].append({"id": _new_id("r"), "tiles": []})
            return g
    g = {
        "id": gid if all(x["id"] != gid for x in doc["groups"]) else _new_id("g"),
        "title": title,
        "icon": icon,
        "rows": [{"id": _new_id("r"), "tiles": []}],
    }
    doc["groups"].append(g)
    return g


def reconcile(
    doc: dict[str, Any],
    existing: set[str],
    snapshots: dict[str, dict[str, Any] | None | tuple[str, dict[str, Any] | None]],
    lang: str = "fr",
) -> tuple[dict[str, Any], bool]:
    """Aligne une disposition sur les connexions réelles.

    - Les tuiles d'une connexion supprimée sont retirées.
    - Une connexion jamais vue ajoute ses tuiles (voir `tiles_for`) une seule fois.
    `snapshots` : identifiant → (type, données), ou données seules pour Proxmox.
    """
    changed = False
    known = [k for k in doc.get("known_connectors", []) if k in existing]
    if len(known) != len(doc.get("known_connectors", [])):
        changed = True
    emptied: set[str] = set()
    for g in doc["groups"]:
        for r in g["rows"]:
            kept = [
                t for t in r["tiles"] if not t["config"].get("connector_id") or t["config"]["connector_id"] in existing
            ]
            if len(kept) != len(r["tiles"]):
                r["tiles"], changed = kept, True
                if not kept:
                    emptied.add(r["id"])
    for cid, entry in snapshots.items():
        ctype, data = entry if isinstance(entry, tuple) else ("proxmox", entry)
        if cid in known or data is None:
            continue
        t = tiles_for(ctype, cid, data, lambda: _new_id("t"))
        home_names = {t["g_home"].lower() for t in GROUP_TITLES.values()}
        home = next(
            (g for g in doc["groups"] if g["id"] == "g_home" or g["title"].strip().lower() in home_names),
            doc["groups"][0],
        )
        home["rows"].insert(0, {"id": _new_id("r"), "tiles": t["home"]})
        if t["infra"]:
            _group(doc, "g_infra", "hard-drives", lang)["rows"][0]["tiles"].extend(t["infra"])
        if t["services"]:
            _group(doc, "g_services", "squares-four", lang)["rows"][0]["tiles"].extend(t["services"])
        known.append(cid)
        changed = True
    # Lignes vidées par ce nettoyage (pas les lignes vides créées volontairement) : retirées
    for g in doc["groups"]:
        rows = [r for r in g["rows"] if r["id"] not in emptied or r["tiles"]]
        if rows and len(rows) != len(g["rows"]):
            g["rows"] = rows
    doc["known_connectors"] = known
    return doc, changed
