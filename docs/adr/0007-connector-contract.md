# 0007. A common contract for connectors

Status: accepted

## Context
Adding support for a new device should not mean touching the core, and one unreachable device must never slow down the rest.

## Decision
Every connector is a class with a configuration model, a secrets model, `test()`, `collect()` and optionally `history()`, plus demo data in the same shape as the real data. The four built-in connectors are registered by the core. Third-party ones can be added through the `mypds.connectors` Python entry point. Each instance is collected on its own, with a timeout and a back-off that stretches up to ten minutes after repeated failures. Network access goes only through the outbound client, locked to the configured host.

## Consequences
- Connectors are tested against recorded responses, without the hardware.
- Tiles are still built into the interface, so a third-party connector can store data but can't yet display its own tiles.
- Connectors run in the same process with no sandbox. Install only connectors you trust.
