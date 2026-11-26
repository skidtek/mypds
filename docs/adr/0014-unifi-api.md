# 0014. Using only the official UniFi API

Status: accepted

## Context
UniFi consoles offer an official local "Network Integration" API (API key, `X-API-Key` header), limited but stable. The web interface relies on a much richer internal API that is undocumented and changes between versions.

## Decision
The official API only (`/proxy/network/integration/v1`), read-only `GET` requests. Live WAN throughput is derived from the gateway's uplink statistics. Speed tests, latency, the ISP name, throughput history and UniFi's own alerts aren't exposed, so MyPDS says so instead of scraping them.

## Consequences
- Survives UniFi updates. Tested on a UDM Pro SE running Network 11, where device models are reported as full names ("UniFi Dream Machine PRO SE"), which MyPDS recognizes.
- A less detailed network view than UniFi's own interface, until the official API grows.
- API keys can't be limited to reading. MyPDS only reads.
