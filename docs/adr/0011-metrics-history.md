# 0011. Where metric history comes from

Status: accepted

## Context
Graphs need history. Proxmox already keeps it (RRD data at hour, day, week, month and year resolution) and exposes it through its API. The other devices mostly don't.

## Decision
Proxmox graphs are read on demand from `rrddata`. MyPDS doesn't store time series. Alerts that depend on duration ("CPU above 85% for 5 minutes") keep their short window in memory.

## Consequences
- History is there from the first connection, with no database growth.
- Resolution is whatever Proxmox provides.
- Graphs for UniFi, Synology and Docker would need local storage. That would be a new decision, backed by real use.
