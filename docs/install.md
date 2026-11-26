# Installing and running MyPDS

MyPDS runs natively in an unprivileged Debian 13 container on Proxmox VE: one systemd service and a local PostgreSQL, with no Docker. This guide covers the automatic install, the manual one, putting it behind a reverse proxy, and everyday care: updates, backups and removal.

**Requirements**
- Proxmox VE 9 (any version that ships the `debian-13-standard` template).
- A container with 2 vCPU, 2 GB of RAM and 12 GB of disk. 1 vCPU and 1 GB are enough to try it out.
- A machine to build the release on: macOS or Linux, with Python 3.13 and Node.js 22. Nothing gets compiled inside the container.

---

## Automatic install

From your computer, in the cloned repository:

```bash
scripts/deploy-proxmox.sh root@your-proxmox-node
```

The script:

1. builds the release;
2. copies it to the node over SSH;
3. asks a few questions. Press Enter to accept a default.

| Question | Default |
|---|---|
| Container ID | next free ID |
| Hostname, storage, disk, CPU, memory, swap | `mypds`, `local-lvm`, 12 GB, 2, 2048 MB, 512 MB |
| Bridge, VLAN, address | `vmbr0`, none, `dhcp` (or a static IP and gateway) |
| HTTPS address behind your reverse proxy | empty means a plain HTTP trial |
| Reverse proxy IP | empty means you'll set it later |
| Admin account (username, display name, password of 12+ characters) | `admin` |

After a summary and a confirmation, the script:

- downloads the Debian 13 template if it's missing;
- creates an unprivileged container (with `nesting=1` and start at boot);
- waits for the network and checks the archive's SHA-256;
- installs MyPDS and creates the admin account;
- checks that the service answers.

The password is typed on the node and passed through standard input, never as a command-line argument.

You can set any answer in advance with an environment variable:

```bash
CTID=130 CT_VLAN=20 PUBLIC_ORIGIN=https://mypds.home.example scripts/deploy-proxmox.sh root@pve
```

The variables are `CTID`, `CT_HOSTNAME`, `CT_STORAGE`, `CT_DISK_GB`, `CT_CORES`, `CT_MEMORY_MB`, `CT_SWAP_MB`, `CT_BRIDGE`, `CT_VLAN`, `CT_IP`, `CT_GW`, `PUBLIC_ORIGIN`, `PROXY_IP`, `ADMIN_USER` and `ADMIN_NAME`. `DEMO=1` adds demo connectors.

### A throwaway container to look around

```bash
scripts/deploy-proxmox.sh root@pve --light
```

This creates a container called `mypds-light`: 1 vCPU, 1 GB of RAM and 6 GB of disk. It doesn't start at boot and comes with demo connectors for Proxmox, UniFi, Synology and Docker. When you're done:

```bash
pct stop <CTID> && pct destroy <CTID>
```

### Trying it over plain HTTP

If you leave the HTTPS address empty, MyPDS is reachable at `http://<container-ip>:8080`, and secure cookies are turned off so that your browser accepts the session. That's fine for a test. Before real use, put it behind HTTPS (see below), then set `MYPDS_COOKIE_SECURE=true` and `MYPDS_PUBLIC_ORIGIN` in `/etc/mypds/mypds.env`.

---

## Manual install

### 1. Create the container

In the Proxmox UI or on the command line. `pveam list local` shows the exact template name. Adjust the ID, storage, bridge and network to your setup:

```bash
pct create 120 local:vztmpl/debian-13-standard_<version>_amd64.tar.zst --hostname mypds --unprivileged 1 --features nesting=1 --cores 2 --memory 2048 --swap 512 --rootfs local-lvm:12 --net0 name=eth0,bridge=vmbr0,ip=dhcp --onboot 1
```

```bash
pct start 120
```

The container needs no mount points and no access to the host's Docker socket.

### 2. Build the release and copy it over

On your computer:

```bash
scripts/build-release.sh
```

This produces `dist/mypds-X.Y.Z.tar.gz` and its `.sha256`. The archive contains the compiled interface and every Python dependency, prebuilt for Debian x86_64 and pinned by hash. Copy both files into the container with `scp`, or `pct push` from the node.

### 3. Install

In the container, as root:

```bash
cd /root && sha256sum -c mypds-X.Y.Z.tar.gz.sha256 && tar xzf mypds-X.Y.Z.tar.gz && ./mypds-X.Y.Z/deploy/install.sh
```

The installer:

- installs Python, PostgreSQL 17 and a few tools from Debian;
- creates a `mypds` system user with no shell;
- creates a database reachable only through a local socket;
- writes `/etc/mypds/mypds.env` and generates the encryption key;
- installs the release, runs the migrations and enables the service and the nightly backup;
- finally asks for an admin username and password.

> **Back up `/etc/mypds/secret.key` now**, in your password manager for example. Without it, the credentials stored in MyPDS can't be decrypted.

### Where things live

```
/opt/mypds/releases/<version>/   the application (read-only, one folder per version)
/opt/mypds/current               link to the running version
/etc/mypds/mypds.env             configuration
/etc/mypds/secret.key            encryption key
/var/lib/mypds/                  application data
/var/backups/mypds/              local backups
journalctl -u mypds              logs
```

---

## Behind a reverse proxy

MyPDS listens on port 8080 and expects a reverse proxy to handle HTTPS. With Nginx Proxy Manager:

1. Add a **Proxy Host** for your domain, pointing to `http://<container-ip>:8080`.
2. Enable **Block Common Exploits**.
3. In the SSL tab, request a certificate (use DNS-01 if the name isn't public), then enable **Force SSL** and **HSTS**.
4. In `/etc/mypds/mypds.env`:

```
MYPDS_PUBLIC_ORIGIN=https://mypds.home.example
MYPDS_TRUSTED_PROXIES='["192.168.1.5/32"]'
MYPDS_COOKIE_SECURE=true
```

5. Restart the service:

```bash
systemctl restart mypds
```

Other proxies (Caddy, Traefik, plain Nginx) work the same way, as long as they forward `X-Forwarded-For`.

With a DHCP address, reserve the container's IP on your router so the proxy keeps finding it. On the Proxmox firewall, allow port 8080 only from the proxy.

## Network flows

| What | From → to | Port |
|---|---|---|
| Users | reverse proxy → MyPDS | 8080/tcp |
| Weather | MyPDS → `api.open-meteo.com`, `geocoding-api.open-meteo.com`, `air-quality-api.open-meteo.com` | 443/tcp |
| Feeds and calendars | MyPDS → the Internet | 443/tcp (80 for plain HTTP feeds) |
| Proxmox | MyPDS → nodes | 8006/tcp |
| UniFi | MyPDS → console | 443/tcp |
| Synology | MyPDS → NAS | 161/udp, 5001/tcp with a DSM account |
| Docker | MyPDS → Docker hosts | 2376/tcp |

Feeds and calendars on private addresses are blocked by default. To allow an internal server, for example a Nextcloud calendar:

```
MYPDS_OUTBOUND_ALLOW_HOSTS='["nextcloud.home.example"]'
```

## Checking that it works

```bash
systemctl status mypds
```

```bash
curl -s http://127.0.0.1:8080/readyz
```

```bash
runuser -u mypds -- bash -c 'set -a; . /etc/mypds/mypds.env; exec /opt/mypds/current/venv/bin/mypds doctor'
```

If the service refuses to start with `status=226/NAMESPACE`, the container doesn't support one of the systemd hardening options. Check that `nesting=1` is set. If it still fails, open an issue with the output of `journalctl -u mypds`.

---

## Updating

From your computer, with the ID of the container to update:

```bash
scripts/deploy-proxmox.sh root@pve --update 106
```

To do it by hand, copy the new archive and its `.sha256` into the container, then run:

```bash
/opt/mypds/current/deploy/update.sh /root/mypds-X.Y.Z.tar.gz
```

Either way, the update:

1. checks the archive;
2. takes a full backup;
3. installs the new version next to the current one;
4. runs the migrations;
5. switches over and checks that the service answers.

If anything fails, it switches back to the previous version. The last three versions are kept.

Read the [changelog](../CHANGELOG.md) before updating.

## Backups

A timer backs everything up every night around 03:15. That includes:

- a dump of the database;
- `/etc/mypds`, **including the encryption key**;
- `/var/lib/mypds`.

Archives go to `/var/backups/mypds/` and the last 14 are kept (`MYPDS_BACKUP_KEEP`). To run one now:

```bash
/opt/mypds/current/deploy/backup.sh
```

Three things matter:

1. **Copy backups out of the container**, to a NAS or Proxmox Backup Server.
2. **Treat them as secrets.** They contain the encryption key.
3. **Restore one from time to time** on a test container. A backup you've never restored is only a hope.

## Restoring

On an existing installation:

```bash
/opt/mypds/current/deploy/restore.sh /var/backups/mypds/mypds-YYYYMMDD-HHMMSS.tar.gz
```

The restore stops the service, recreates the database, puts back the configuration, the key and the data, runs the migrations and restarts.

On a brand-new container, install the same version or a newer one first, then run the restore.

If your calendars or connections show "unknown key ID" after a restore, the key doesn't match the database. Put the right `secret.key` back (mode 0400, owned by `mypds`) and restart.

## Uninstalling

First take a last backup and copy it somewhere safe. If you like, export your layout (Settings → Layout) and your feeds (Settings → News → Export OPML).

```bash
/opt/mypds/current/deploy/uninstall.sh
```

This removes the service and the application, and keeps the database, configuration, data and backups. To remove everything (it asks twice):

```bash
/opt/mypds/current/deploy/uninstall.sh --purge
```

Often the simplest option is to delete the container itself, once you've saved your backups.
