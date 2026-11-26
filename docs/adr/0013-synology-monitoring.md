# 0013. Monitoring Synology with SNMP v3 and an optional DSM account

Status: accepted

## Context
DSM's web APIs for system and storage status are partly undocumented, vary between versions, and usually need an admin account. Synology does document an SNMP MIB.

## Decision
SNMP v3 in authPriv mode, with a dedicated read-only user, for hardware and storage: system state, fans, temperatures, CPU, memory, disks, RAID groups and volumes. The DSM web API is optional, with a dedicated account, for DSM updates and Hyper Backup status. Its availability is detected through `SYNO.API.Info`, and MyPDS signs out after each check. Whatever DSM doesn't expose is shown as unavailable.

## Consequences
- Basic monitoring needs no DSM account at all.
- Adds the `pysnmp` dependency (pure Python, async).
- Marked experimental until validated on real hardware.
