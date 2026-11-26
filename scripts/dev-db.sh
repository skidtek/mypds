#!/usr/bin/env bash
# Development PostgreSQL 17, local to the project (port 5433, data in .dev/).
# Usage: scripts/dev-db.sh start|stop|status
set -euo pipefail
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGBIN="${PGBIN:-/opt/homebrew/opt/postgresql@17/bin}"
DATA="$ROOT/.dev/pgdata"; RUN="$ROOT/.dev/run"; PORT="${MYPDS_DEV_PGPORT:-5433}"
mkdir -p "$RUN"
case "${1:-start}" in
  start)
    if [ ! -d "$DATA" ]; then
      "$PGBIN/initdb" -D "$DATA" -U mypds --auth=trust --encoding=UTF8 --locale=C >/dev/null
    fi
    "$PGBIN/pg_ctl" -D "$DATA" -l "$ROOT/.dev/postgres.log" \
      -o "-p $PORT -k $RUN -c listen_addresses=''" status >/dev/null 2>&1 || \
    "$PGBIN/pg_ctl" -D "$DATA" -l "$ROOT/.dev/postgres.log" \
      -o "-p $PORT -k $RUN -c listen_addresses=''" -w start >/dev/null
    "$PGBIN/psql" -h "$RUN" -p "$PORT" -U mypds -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname='mypds'" | grep -q 1 || \
      "$PGBIN/createdb" -h "$RUN" -p "$PORT" -U mypds mypds
    echo "Dev PostgreSQL ready: socket $RUN, port $PORT, database mypds"
    ;;
  stop) "$PGBIN/pg_ctl" -D "$DATA" -w stop ;;
  status) "$PGBIN/pg_ctl" -D "$DATA" status ;;
esac
