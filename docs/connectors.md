# Connectors

A connector is how MyPDS reads the state of one of your devices. You add them in **Settings → Connections**. Only admins can do that.

Every connector follows the same rules:

- **Read-only.** MyPDS only sends read requests and never changes anything on your devices.
- **Your own credentials, kept encrypted.** Create an account or token dedicated to MyPDS, with the smallest role that works. MyPDS encrypts it and never shows it again.
- **Failures stay contained.** If a device can't be reached, its tiles say so. MyPDS retries less and less often (up to every ten minutes) and the rest of the page carries on.
- **Demo mode.** Each connector can run on realistic fake data instead of a real device. A "Demo" badge always marks it.

You can paste an address as a full URL (`https://192.168.1.1/`). MyPDS keeps only the host and port.

---

## Proxmox VE: tested

**What you see:** cluster state and quorum, nodes, VMs and containers (running or stopped), CPU, memory and storage, the last hour of CPU per node, recent failed tasks and backups. Data refreshes every 15 seconds.

**Alerts:** node offline or quorum lost (critical); guest stopped (warning, unless you mark it as "started on demand"); CPU, memory or storage above your thresholds; failed backup or task in the last 24 hours. Thresholds can be set in Settings → Cockpit.

**Setup:** run this in a root shell on any node.

```bash
pveum user add mypds@pve --comment "My Personal Digital Space"
```

```bash
pveum acl modify / --users mypds@pve --roles PVEAuditor
```

```bash
pveum user token add mypds@pve monitor --privsep 0
```

Copy the `value` it prints (it's shown only once). In MyPDS, the token ID is `mypds@pve!monitor`.

Proxmox uses a self-signed certificate by default. Paste its fingerprint so the connection stays verified:

```bash
pvenode cert info --output-format json | grep -i fingerprint
```

**Network:** MyPDS → each node, port 8006/tcp.

---

## UniFi Network: tested

Tested on a UniFi Dream Machine Pro SE running Network 11. Other consoles running the official Integration API should work too.

**What you see:** the gateway (model, uptime, CPU, memory), live Internet throughput, devices online or offline, pending firmware updates, and clients by type (Wi-Fi, wired, VPN). Data refreshes every 30 seconds.

**Alerts:** gateway offline (critical), another device offline (warning).

**Setup:**
1. In UniFi Network, open **Settings → Control Plane → Integrations** and create an API key.
2. Copy it (it's shown only once) and paste it into MyPDS.
3. The console uses a self-signed certificate. To get its fingerprint, run:

```bash
openssl s_client -connect 192.168.1.1:443 </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256
```

MyPDS uses only the official API (see [ADR 0014](adr/0014-unifi-api.md)). That API doesn't expose speed tests, latency, the ISP name or alert history, so MyPDS doesn't show them. UniFi API keys can't be restricted to reading, but MyPDS only sends `GET` requests.

**Network:** MyPDS → console, port 443/tcp.

---

## Synology DSM: experimental

The code is complete and tested against recorded responses, but hasn't run against a real NAS yet. If you try it, please tell me how it goes.

**What you see:** model and DSM version, system and power state, fans, temperatures, CPU and memory, each disk (status, health, temperature), RAID groups and volumes with free space, and Hyper Backup tasks if you add a DSM account. Data refreshes every 60 seconds.

**Alerts:** hardware fault (critical), degraded or crashed volume (critical), failing disk, volume almost full, failed Hyper Backup task (warning).

**Setup:**
1. In DSM, open **Control Panel → Terminal & SNMP → SNMP**. Enable the SNMP service and tick SNMPv3 only.
2. Create a SNMP user (for example `mypds`) with SHA authentication and AES privacy. Each password must be at least 8 characters.
3. In the NAS firewall, allow UDP port 161 from the MyPDS container.
4. Optional, for Hyper Backup: create a dedicated DSM account without two-factor authentication. MyPDS signs out after each check.

**Network:** MyPDS → NAS, port 161/udp, plus port 5001/tcp if you added a DSM account.

---

## Docker: experimental

The code is complete and tested against recorded responses, but hasn't run against a real remote host yet.

**What you see:** engine version, containers (running, stopped, restarting), their health checks, CPU and memory. Data refreshes every 30 seconds.

**Alerts:** container stopped (warning, unless marked as "started on demand"), container unhealthy (warning).

**Setup:** MyPDS connects to the Docker Engine API over mutual TLS on port 2376, the method documented by Docker. It works with any reachable host: a VM, an LXC, a NAS or another machine.

1. On the Docker host, create a certificate authority, a server certificate that includes the host's address, and a client certificate dedicated to MyPDS. Docker's guide, "Protect the Docker daemon socket", walks through it.
2. Start `dockerd` with `--tlsverify` and the server certificates, listening on port 2376.
3. Paste the CA certificate, the client certificate and the client key into MyPDS.

**Please read this before you set it up.** Docker has no read-only access. That client certificate gives full control of the host. MyPDS only sends read requests, but if the MyPDS container were compromised, the Docker host would be too. Use a certificate that only MyPDS has, so you can revoke it, and open port 2376 only to the MyPDS container. The reasoning is in [ADR 0012](adr/0012-remote-docker-access.md).

**Network:** MyPDS → Docker host, port 2376/tcp.

---

## Writing a connector

Connectors live in `backend/src/mypds/connectors/<name>/`. Each one declares:

- a configuration model and a secrets model (Pydantic);
- a `test()` that checks the connection;
- a `collect()` that returns a snapshot;
- demo data in the same shape as the real thing.

Alert rules go in `alerts/rules.py` and tiles in `frontend/src/spaces/cockpit/tiles/`. The UniFi connector is a good, small example to start from. See [CONTRIBUTING.md](../CONTRIBUTING.md).
