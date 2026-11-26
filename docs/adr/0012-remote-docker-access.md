# 0012. Reaching remote Docker hosts

Status: accepted

## Context
The Docker Engine API has no permission levels: any access is equivalent to root on the host. Users run Docker in many places, such as VMs, LXCs, a Synology or another machine.

Three options were considered:

1. A small MyPDS agent on each Docker host, exposing only the endpoints needed, with scoped tokens.
2. Docker's own mutual TLS (`dockerd --tlsverify`, port 2376).
3. A filtering socket proxy behind a TLS reverse proxy.

## Decision
**Option 2, mutual TLS.** It is documented by Docker, works on any host and needs nothing extra installed. To compensate for the all-or-nothing access:

- MyPDS only calls read endpoints: version, info, container list, inspect and one-shot stats.
- The client certificate and key are encrypted at rest, never sent to the browser, and written to a private temporary file only while the TLS context is loaded.
- The host's CA is always verified.
- The documentation and the connection form ask for a certificate dedicated to MyPDS, with port 2376 open only to the MyPDS container.

## Consequences
- Simple to set up, nothing to maintain on the Docker hosts.
- Residual risk, stated in [SECURITY.md](../../SECURITY.md): a compromised MyPDS means root on the Docker hosts it watches. Option 1 remains the path if device control is ever added.
