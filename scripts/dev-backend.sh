#!/usr/bin/env bash
# Runs the back end in development (with the project's local PostgreSQL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/dev-db.sh" start >/dev/null
set -a; . "$ROOT/.dev/dev.env"; set +a
exec "$ROOT/backend/.venv/bin/python" -m mypds.cli serve "$@"
