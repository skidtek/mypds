#!/usr/bin/env bash
# Installs My Personal Digital Space on Debian 13 (an unprivileged LXC is recommended).
# Usage (as root), from the extracted release:  ./deploy/install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(dirname "$HERE")"
. "$HERE/lib.sh"

require_root
check_platform
[ -f "$SRC/VERSION" ] && [ -d "$SRC/wheels" ] || die "Run this script from an extracted release archive (VERSION and wheels/ expected)."
[ -L "$APP_DIR/current" ] && die "Already installed. To update: deploy/update.sh <archive>."

say "System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv postgresql ca-certificates curl iputils-ping >/dev/null

say "System user $APP_USER"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin "$APP_USER"
install -d -o "$APP_USER" -g "$APP_USER" -m 0750 "$DATA_DIR"
install -d -o root -g "$APP_USER" -m 0750 "$ETC_DIR"
install -d -o root -g root -m 0700 "$BACKUP_DIR"
install -d -o root -g root -m 0755 "$APP_DIR" "$APP_DIR/releases"

say "PostgreSQL database (Unix socket, peer authentication)"
systemctl enable --now postgresql >/dev/null
runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$APP_USER'" | grep -q 1 || \
  runuser -u postgres -- psql -qc "CREATE ROLE $APP_USER LOGIN"
runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='mypds'" | grep -q 1 || \
  runuser -u postgres -- createdb -O "$APP_USER" mypds

say "Configuration"
if [ ! -f "$ETC_DIR/mypds.env" ]; then
  install -o root -g "$APP_USER" -m 0640 "$HERE/mypds.env.example" "$ETC_DIR/mypds.env"
fi
if [ ! -f "$ETC_DIR/secret.key" ]; then
  head -c 32 /dev/urandom > "$ETC_DIR/secret.key"
  chown "$APP_USER:$APP_USER" "$ETC_DIR/secret.key"
  chmod 0400 "$ETC_DIR/secret.key"
  warn "Encryption key created: $ETC_DIR/secret.key. Back it up somewhere safe (see docs/install.md#backups)."
fi

say "Unprivileged ping (ICMP checks)"
gid="$(getent group "$APP_USER" | cut -d: -f3)"
echo "net.ipv4.ping_group_range = 0 $gid" > /etc/sysctl.d/60-mypds-ping.conf
sysctl -q -p /etc/sysctl.d/60-mypds-ping.conf 2>/dev/null || warn "ping_group_range cannot be changed here: ICMP checks will be disabled."

dest="$(install_release "$SRC" | tail -1)"
ln -sfn "$dest" "$APP_DIR/current"

say "Migrations"
run_as_app "$APP_DIR/current/venv/bin/mypds" migrate

say "systemd services"
install -m 0644 "$HERE/systemd/mypds.service" "$HERE/systemd/mypds-backup.service" "$HERE/systemd/mypds-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mypds.service mypds-backup.timer >/dev/null

if [ -n "${MYPDS_NO_ADMIN_PROMPT:-}" ]; then
  : # the caller creates the account (deploy/proxmox/create-ct.sh)
elif [ -t 0 ]; then
  say "Admin account"
  read -rp "Admin username [admin]: " admin; admin="${admin:-admin}"
  read -rp "Display name [$admin]: " display; display="${display:-$admin}"
  run_as_app "$APP_DIR/current/venv/bin/mypds" create-user "$admin" --display-name "$display" --role admin
else
  warn "No interactive terminal: create the admin account with"
  warn "  sudo -u $APP_USER bash -c 'set -a; . $ETC_DIR/mypds.env; $APP_DIR/current/venv/bin/mypds create-user admin --role admin'"
fi

if wait_ready; then
  say "Installation complete. The service is listening on port $(sed -n 's/^MYPDS_PORT=//p' "$ETC_DIR/mypds.env")."
  say "Next: set up your reverse proxy (docs/install.md#behind-a-reverse-proxy), then MYPDS_TRUSTED_PROXIES and MYPDS_PUBLIC_ORIGIN."
else
  die "The service does not answer on /readyz. To investigate: journalctl -u mypds -n 100; $APP_DIR/current/venv/bin/mypds doctor"
fi
