# 0006. Encrypting stored credentials

Status: accepted

## Context
Proxmox tokens, UniFi keys, SNMP and DSM passwords, Docker client keys and calendar links must not be readable from a copy of the database.

## Decision
AES-256-GCM with a master key kept in `/etc/mypds/secret.key`, outside the database and readable only by the service. Each value gets a random nonce, plus associated data that binds it to its owner and field, so it can't be moved to another record. A key identifier leaves room for rotation. The API never returns secrets and exports never include them.

## Consequences
- A leaked database dump alone reveals no credential.
- The key must be backed up separately. Losing it means entering every credential again.
- A secrets vault such as HashiCorp Vault was considered and judged out of proportion for a homelab.
