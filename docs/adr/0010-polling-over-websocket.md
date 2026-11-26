# 0010. Polling instead of WebSockets, for now

Status: accepted

## Context
The original plan was one multiplexed WebSocket per tab, to push updates to tiles. In practice, data changes every 15 to 60 seconds, and the cockpit is opened and closed often.

## Decision
The interface fetches each widget independently over REST and refreshes on a timer: 30 seconds for the cockpit, several minutes for weather, news and calendars. Refreshing pauses while the tab is hidden. The back end serves the latest snapshot from memory, so a refresh costs almost nothing.

## Consequences
- Much simpler: no reconnection logic, nothing to resynchronize, and no WebSocket needed at the reverse proxy.
- Updates arrive up to one interval late, which is acceptable for a dashboard.
- A WebSocket can come later, if device control or live logs need it.
