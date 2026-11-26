# 0001. Python 3.13 and FastAPI for the back end

Status: accepted

## Context
The back end mostly waits on the network. It talks to Proxmox, UniFi, a NAS, feeds and calendars, often at the same time. It should run on what Debian 13 ships, so security updates arrive through `apt`.

## Decision
FastAPI on Uvicorn, using Debian's Python 3.13 in a virtual environment. Pydantic v2 validates every input, SQLAlchemy 2 (async) with asyncpg talks to the database, and httpx makes outbound calls. A single process serves the API and the interface and runs the background jobs.

## Consequences
- Async fits the workload, and the Python ecosystem has mature libraries for RSS, ICS and SNMP.
- One process keeps installation and debugging simple. Anything blocking, such as parsing a large feed, has to run in a thread so it doesn't freeze the event loop.
- Go was considered: a single small binary, but weaker libraries for feeds and calendars.
