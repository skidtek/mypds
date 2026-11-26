# Changelog

Notable changes to MyPDS. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [1.0.0]: first public release

The first version I'm comfortable sharing. It runs my own homelab on Proxmox every day.

### Start page
- Search with Google, Bing, DuckDuckGo, Qwant or a custom engine.
- Weather from Open-Meteo: current conditions, forecast, wind or rain depending on the sky, air quality, UV index, sunrise and sunset, and an animated sky.
- Calendars from ICS links, including password-protected ones.
- News from RSS and Atom feeds, grouped by category, with OPML import and export.
- To-do lists with round or square checkboxes. Completed items are kept with their creation and completion dates.
- Sticky notes with tabs, six colors and four paper textures.
- Free grid that stays within the search bar's width: drag, resize, hide, keyboard support. Separate phone layout, plus layout export and import.

### Cockpit
- Tabs, rows and tiles, arranged in an editor. The arrangement is kept on phones.
- **Proxmox VE**: cluster summary, nodes with CPU history, VM and container tiles that link to their services.
- **UniFi Network** (official API): gateway, live WAN throughput, devices, clients, firmware updates.
- **Synology DSM** (SNMP v3, optional DSM account): hardware, disks, RAID, volumes, Hyper Backup. *Experimental.*
- **Docker** (mutual TLS): containers, health, CPU and memory. *Experimental.*
- Demo mode for every connector, always labeled.
- Alerts that open and resolve on their own, with adjustable thresholds. A guest can be marked as "started on demand" so that stopping it isn't an alert.
- Header with a greeting, overall status, latest activity and alert count. Clicking any of them jumps to the matching tile.

### Everywhere
- Frosted glass themes, light and dark, adjustable blur, transparency and accent color. Built-in wallpapers, or upload your own.
- Your own name, logo (above, left of or right of the title) and colors.
- English and French interface.
- Profile with a photo you can crop, password change and open sessions.

### Security
- Read-only connectors, credentials encrypted with AES-256-GCM, server-side sessions with CSRF protection, login throttling, a strict Content Security Policy, a guarded outbound client against SSRF, TLS fingerprint pinning, and an audit log. See [SECURITY.md](SECURITY.md).

### Installation
- One command from your computer creates and installs a Debian 13 container on Proxmox (`scripts/deploy-proxmox.sh`).
- `--light` creates a small throwaway container with demo data. `--update <CTID>` upgrades in place, with a backup first and an automatic rollback.
- Offline install from a hash-pinned release archive, nightly backups, restore and uninstall scripts.

[1.0.0]: https://github.com/skidtek/mypds/releases/tag/v1.0.0
