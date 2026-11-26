# 0004. Native install in an LXC container, no Docker

Status: accepted

## Context
Most homelab users on Proxmox prefer a small LXC container to a VM running Docker. The install must be reproducible, easy to update and easy to roll back, without asking anyone to edit code.

## Decision
A release is a single archive with the compiled interface and every Python dependency as prebuilt wheels, pinned by hash. It is built outside the container. Each version installs into `/opt/mypds/releases/<version>`, with a `current` link pointing to the active one. A hardened systemd unit runs the service as an unprivileged user. Configuration lives in `/etc/mypds`, data in `/var/lib/mypds`. TLS is left to the user's reverse proxy.

`scripts/deploy-proxmox.sh` drives the whole thing from the user's computer: it creates the container, installs, updates in place, or sets up a throwaway demo container.

## Consequences
- Updates switch atomically and roll back by switching the link back.
- No compiler and no Node.js inside the container. Installation works without access to PyPI or npm.
- A build step is needed on a Mac or Linux machine, or in CI.
