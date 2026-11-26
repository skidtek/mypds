# 0003. PostgreSQL 17

Status: accepted

## Context
MyPDS stores users, layouts as JSON documents, connections, alerts, feeds, to-dos and an audit log. The volume is small, but the data matters.

## Decision
PostgreSQL 17 as packaged by Debian 13, reached only through a Unix socket with peer authentication. Alembic manages the schema, and layouts are stored as `jsonb` and validated by the application. MyPDS keeps no time-series table: see [ADR 0011](0011-metrics-history.md).

## Consequences
- One database, backed up with a single `pg_dump`.
- No password to manage, and PostgreSQL doesn't listen on the network.
- PostgreSQL 18 would require the upstream repository and brings nothing needed here. A later major upgrade can use `pg_upgradecluster`.
