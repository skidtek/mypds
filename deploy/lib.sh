# shellcheck shell=bash disable=SC2034
# Shared helpers for the deploy scripts (sourced, not run on its own).
set -euo pipefail
# A locale forwarded over SSH (e.g. en_US.UTF-8 from a Mac) may not exist in the container: use the built-in one
export LC_ALL=C.UTF-8
APP_DIR=/opt/mypds
ETC_DIR=/etc/mypds
DATA_DIR=/var/lib/mypds
BACKUP_DIR=/var/backups/mypds
APP_USER=mypds
SERVICE=mypds.service

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Run this as root (sudo)."; }

check_platform() {
  [ -r /etc/os-release ] || die "/etc/os-release not found."
  . /etc/os-release
  [ "${ID:-}" = "debian" ] || die "Debian is required (found: ${ID:-unknown})."
  [ "${VERSION_ID%%.*}" -ge 13 ] 2>/dev/null || die "Debian 13 (trixie) or newer is required (found: ${VERSION_ID:-?})."
  [ "$(uname -m)" = "x86_64" ] || die "An x86_64 machine is required."
}

wait_ready() {
  local port; port="$(sed -n 's/^MYPDS_PORT=//p' "$ETC_DIR/mypds.env" | tail -1)"; port="${port:-8080}"
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:$port/readyz" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

# Installs an extracted release into $APP_DIR/releases/<version>, with a fresh virtualenv.
install_release() {
  local src="$1" version
  version="$(cat "$src/VERSION")"
  local dest="$APP_DIR/releases/$version"
  [ -e "$dest" ] && die "Version $version is already installed in $dest."
  say "Installing version $version"
  mkdir -p "$dest"
  cp -R "$src/static" "$src/deploy" "$src/VERSION" "$dest/"
  python3 -m venv "$dest/venv"
  "$dest/venv/bin/pip" install --quiet --no-index --find-links "$src/wheels" --require-hashes -r "$src/requirements.lock"
  chmod +x "$dest"/deploy/*.sh
  chown -R root:root "$dest"
  echo "$dest"
}

# Runs a command as the application user, with the configuration loaded.
run_as_app() {
  runuser -u "$APP_USER" -- bash -c 'set -a; . /etc/mypds/mypds.env; set +a; exec "$@"' _ "$@"
}
