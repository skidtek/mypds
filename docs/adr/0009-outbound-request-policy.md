# 0009. One guarded client for every outbound request

Status: accepted

## Context
Feed, calendar and image URLs come from users. The MyPDS container usually sits on an infrastructure network next to admin interfaces. It must not become a way to reach them.

## Decision
All outbound traffic goes through a single client that:

- resolves DNS itself;
- refuses private, loopback, link-local, multicast and reserved addresses for user-supplied URLs;
- connects to the address it validated, which defeats DNS rebinding;
- checks every redirect again;
- caps response size and duration;
- ignores proxy environment variables.

Connectors are locked to the host their admin configured, where private addresses are expected. Self-signed devices are verified by certificate fingerprint pinning. An admin can allow specific internal hosts for feeds and calendars.

## Consequences
- The back end can't be used to reach internal admin pages through a crafted feed URL.
- A calendar hosted on the LAN has to be explicitly allowed.
