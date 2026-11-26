# Security

MyPDS stores credentials for the machines that run your home: Proxmox tokens, a UniFi API key, SNMP passwords, Docker client certificates. I take that seriously. This page describes what is actually in place today, what is not, and how to tell me when something is wrong.

## Reporting a vulnerability

Please **don't open a public issue** for a security problem. Use GitHub's private reporting instead: **Security → Report a vulnerability** on the repository page. Only the maintainers can see the report.

I'll acknowledge your report within a week. Once a fix is ready, I'll publish a release and credit you, unless you'd rather stay anonymous. This is a personal project maintained in my spare time, so there is no bug bounty, only my sincere thanks.

Only the latest release receives security fixes.

## How MyPDS is meant to be deployed

MyPDS is built for a trusted network: your LAN, or a VPN such as WireGuard, behind a reverse proxy that terminates TLS (Nginx Proxy Manager, Caddy, Traefik…). **It is not designed to be exposed directly to the Internet.** The threat model below assumes that.

## What is in place

**Accounts and sessions**
- Passwords are hashed with Argon2id and must be at least 12 characters long.
- After 5 failed logins in 15 minutes, for a username or an IP address, further attempts are refused.
- Sessions live on the server. The browser only holds a random 256-bit identifier in an `HttpOnly`, `SameSite=Strict` cookie (`__Host-` prefixed and `Secure` behind HTTPS). The database only stores its SHA-256 hash.
- Changing state requires a CSRF token sent in a header, and the request origin is checked.
- You can see your open sessions and close them from your profile.

**Credentials for your devices**
- Credentials are encrypted with AES-256-GCM, each bound to its connection and field so it can't be swapped with another one. The master key is a separate file (`/etc/mypds/secret.key`, readable only by the service), not the database.
- The API never sends a credential back to the browser. It only says whether one is set.
- Calendar links are treated as secrets too, since they often contain an access token.

**Connections to your devices**
- Every connector is **read-only**: it only sends read requests. MyPDS cannot start, stop or change anything.
- Proxmox: a token with the `PVEAuditor` role is enough. Synology: SNMP v3 in authPriv mode. A DSM account is optional.
- Self-signed certificates are handled by pinning their SHA-256 fingerprint, not by turning verification off.

**Outbound requests**
- Every request leaves through a single client.
- Feeds, calendars and images come from user input. For those, it resolves DNS itself, refuses private, loopback, link-local and reserved addresses, connects to the address it validated (so DNS rebinding doesn't work), and checks redirects again.
- Response sizes and timeouts are capped. XML is parsed with entity expansion disabled.
- To allow an internal host on purpose, list it in `MYPDS_OUTBOUND_ALLOW_HOSTS`.

**In the browser**
- A strict Content Security Policy: scripts come only from the app itself, and the page cannot be framed.
- `nosniff`, `no-referrer`, a restrictive `Permissions-Policy` and `Cross-Origin-Opener-Policy`.
- Feed content is reduced to plain text before it is displayed. Uploaded images are accepted only if their actual bytes are PNG, JPEG or WebP, whatever the file name says. SVG is refused because it can carry scripts.

**On the system**
- The service runs as a dedicated user with no shell, under a hardened systemd unit (`NoNewPrivileges`, `ProtectSystem=strict`, no capabilities).
- PostgreSQL listens only on a Unix socket.
- Release archives come with a SHA-256 checksum, and Python dependencies are installed offline from the archive, each one checked against its pinned hash.
- An audit log records sign-ins, password changes, connection changes, imports and branding changes, without any secret values.

## Known limits

I'd rather you hear these from me:

- **Docker access is all or nothing.** A Docker client certificate gives full control of that Docker host. MyPDS only reads, but if your MyPDS container were compromised, so would be the Docker hosts it watches. Use a certificate dedicated to MyPDS, and open port 2376 only to the MyPDS container. More in [ADR 0012](docs/adr/0012-remote-docker-access.md).
- **UniFi API keys can't be limited to reading.** MyPDS only reads, but the key itself could do more.
- **No two-factor authentication yet.** That's on the list, before any feature that controls devices.
- **The master key protects credentials at rest, not a compromised server.** Someone with root inside the container can read both the database and the key. Back up `secret.key` separately and treat backups as secrets.
- `style-src` allows inline styles, which the interface needs for user-chosen colors and layout positions. Scripts stay strict.

## Keeping your installation safe

- Update when a release comes out (`scripts/deploy-proxmox.sh root@node --update <CTID>`). The update script backs up first and rolls back if the new version doesn't start.
- Give MyPDS its own accounts and tokens on each device, with the smallest role that works.
- Restrict access to port 8080 to your reverse proxy using the Proxmox firewall.
- Keep `/etc/mypds/secret.key` in your password manager.
