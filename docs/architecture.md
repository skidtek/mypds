# Architecture

MyPDS is deliberately small: one process, one database, one container. This page is the map. The reasons behind each choice are in the [decision records](adr/README.md).

```
           browser
              │  HTTPS
     ┌────────▼────────┐
     │  reverse proxy  │   Nginx Proxy Manager, Caddy, Traefik…
     └────────┬────────┘
              │  HTTP :8080
┌─────────────▼──────────────────────────────────────────────┐
│ Debian 13 LXC (unprivileged)                               │
│                                                            │
│  mypds.service: Uvicorn + FastAPI, runs as user "mypds"    │
│   ├─ /            compiled interface (static files)        │
│   ├─ /api/v1/…    REST API                                 │
│   ├─ /healthz /readyz                                      │
│   ├─ connector loop   (Proxmox 15 s, UniFi 30 s, …)        │
│   └─ scheduler        (feeds, calendars, session cleanup)  │
│            │ Unix socket                │ guarded client   │
│     ┌──────▼──────┐                     │                  │
│     │ PostgreSQL  │                     │                  │
│     └─────────────┘                     │                  │
└─────────────────────────────────────────┼──────────────────┘
                                          ▼
          Proxmox · UniFi · Synology · Docker · Open-Meteo · feeds · calendars
```

## Guiding rules

1. **The browser only ever talks to MyPDS.** It never sees a device address, a credential or a calendar link.
2. **Read-only.** Connectors observe and never act.
3. **Real data, or fake data that says so.** Demo mode exists for every connector and is always labeled.
4. **Contained failures.** Each connection is collected on its own, with a timeout and a back-off. A dead device turns its tiles grey and nothing else.
5. **Two spaces, two layout engines.** The start page and the cockpit share the design system and nothing about layout.

## Back end (`backend/src/mypds`)

| Module | Role |
|---|---|
| `core/` | settings, database, the guarded outbound client (`net.py`), encryption, security headers, scheduler |
| `auth/` | accounts, sessions, CSRF, profile and avatar, audit log |
| `config/` | preferences, branding, wallpapers |
| `landing/` | start page layout documents |
| `cockpit/` | cockpit layout documents (Tab › Row › Tile) and custom icons |
| `widgets/` | weather, calendar, news, to-dos, notes |
| `connectors/` | the connector contract (`sdk.py`), the collection loop, and one folder per device type |
| `alerts/` | rules per connector type and the engine that opens and resolves alerts |
| `migrations/` | Alembic schema history |

Connectors are collected in the background. Their latest snapshot stays in memory, so the cockpit's requests are answered from memory and never wait on a device. After each collection, the alert engine compares the snapshot with the rules and opens or resolves alerts in the database.

## Interface (`frontend/src`)

| Folder | Role |
|---|---|
| `app/` | router, login, top bar, brand header |
| `design-system/` | tokens, glass surfaces, wallpapers, shared components and helpers |
| `spaces/landing/` | start page and its free grid |
| `spaces/cockpit/` | cockpit, tiles, editor |
| `widgets/` | one folder per start page widget |
| `settings/` | every settings screen |
| `stores/` | Pinia stores |
| `i18n/` | translations (French keys, English catalog) |

Each widget and tile loads its own data and refreshes on a timer while the tab is visible. Going from the start page to the cockpit is instant: the cockpit's code and data are fetched in advance, as soon as the page is idle.

## Data

PostgreSQL holds accounts and sessions, preferences, both layouts, connections (with encrypted credentials), alerts, feeds and their items, calendars, to-dos, notes, uploaded images and the audit log. There are no time series: graph history comes from Proxmox itself ([ADR 0011](adr/0011-metrics-history.md)).

## Release and install

`scripts/build-release.sh` produces a single archive: the compiled interface, every Python dependency as a prebuilt wheel pinned by hash, and the deploy scripts. `deploy/install.sh` installs it offline inside the container. `scripts/deploy-proxmox.sh` drives the whole thing from your computer. See [install.md](install.md).
