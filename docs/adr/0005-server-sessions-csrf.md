# 0005. Server-side sessions and CSRF tokens

Status: accepted

## Context
MyPDS is a same-origin browser application that holds credentials to the user's infrastructure. Sessions must be revocable on the spot.

## Decision
An opaque random session identifier in an `HttpOnly`, `SameSite=Strict` cookie, `__Host-` prefixed and `Secure` behind HTTPS. The database stores only its SHA-256 hash. Requests that change state carry a CSRF token in a header, and the origin is checked. Passwords are hashed with Argon2id. Repeated failed logins are throttled per username and per IP. Identity is kept separate from the session, so an OIDC provider can be added later.

## Consequences
- Closing a session takes effect immediately, and the browser never holds a token that scripts could read.
- A small amount of server state, negligible at this scale.
- Two-factor authentication is not implemented yet. It is planned before any feature that controls devices.
