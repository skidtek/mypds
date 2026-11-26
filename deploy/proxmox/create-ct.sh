#!/usr/bin/env bash
# Creates a Debian 13 LXC container on a Proxmox VE node and installs My Personal Digital Space in it.
#
# Run as root on the node:  ./create-ct.sh /path/to/mypds-X.Y.Z.tar.gz
# (scripts/deploy-proxmox.sh, on your computer, copies the files and runs it for you.)
#
# It asks a few questions (default in brackets). Each answer can be set in advance with an
# environment variable, for an install without questions:
#   CTID, CT_HOSTNAME, CT_STORAGE, CT_DISK_GB, CT_CORES, CT_MEMORY_MB, CT_SWAP_MB,
#   CT_BRIDGE, CT_VLAN, CT_IP (dhcp or 192.168.1.20/24), CT_GW, PUBLIC_ORIGIN, PROXY_IP,
#   ADMIN_USER, ADMIN_NAME. The admin password is always asked for, never passed as an argument.
# Options: DEMO=1 adds demo connectors (fake data, always labeled), CT_ONBOOT=0 disables start
#   at boot, CT_TAGS replaces the "mypds" tag.
set -euo pipefail

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
ask() { # ask VAR "Question" default (asks nothing if VAR is already set)
  local var="$1" question="$2" default="${3:-}" answer
  if [ -n "${!var:-}" ]; then return; fi
  read -rp "$question [$default]: " answer
  printf -v "$var" '%s' "${answer:-$default}"
}

# ---------- Checks ----------
[ "$(id -u)" -eq 0 ] || die "Run this as root on the Proxmox node."
if ! command -v pct >/dev/null || ! command -v pveam >/dev/null; then
  die "Proxmox commands (pct, pveam) not found: run this script on a Proxmox VE node."
fi
ARCHIVE="${1:-}"
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || die "Usage: $0 /path/to/mypds-X.Y.Z.tar.gz (with its .sha256 file next to it)"
ARCHIVE="$(cd "$(dirname "$ARCHIVE")" && pwd)/$(basename "$ARCHIVE")"
[ -f "$ARCHIVE.sha256" ] || die "Checksum file not found: $ARCHIVE.sha256"
say "Checking the archive"
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256" >/dev/null) || die "SHA-256 mismatch: the archive is corrupted or was modified."
NAME="$(basename "$ARCHIVE" .tar.gz)"
[ -t 0 ] || warn "No interactive terminal: every value must come from environment variables."

# ---------- Questions ----------
echo
say "Container"
ask CTID "Container ID" "$(pvesh get /cluster/nextid)"
pct status "$CTID" >/dev/null 2>&1 && die "Container $CTID already exists."
ask CT_HOSTNAME "Hostname" "mypds"
default_storage="$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active" {print $1}' | grep -m1 -x 'local-lvm\|local-zfs' || true)"
[ -n "$default_storage" ] || default_storage="$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active" {print $1; exit}')"
ask CT_STORAGE "Disk storage ($(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active" {printf "%s ", $1}'))" "$default_storage"
ask CT_DISK_GB "Disk size (GB)" "12"
ask CT_CORES "CPU cores" "2"
ask CT_MEMORY_MB "Memory (MB)" "2048"
ask CT_SWAP_MB "Swap (MB)" "512"

echo
say "Network"
ask CT_BRIDGE "Bridge" "vmbr0"
ask CT_VLAN "VLAN tag (empty for none)" ""
ask CT_IP "Address: \"dhcp\" or a static IP with prefix (e.g. 192.168.1.20/24)" "dhcp"
if [ "$CT_IP" != "dhcp" ]; then
  [[ "$CT_IP" =~ ^[0-9.]+/[0-9]{1,2}$ ]] || die "Invalid address: $CT_IP (expected format: 192.168.1.20/24)"
  ask CT_GW "Gateway" ""
  [ -n "$CT_GW" ] || die "A gateway is required with a static IP."
fi

echo
say "Access"
echo "    HTTPS address MyPDS will have behind your reverse proxy (e.g. https://mypds.home.example)."
echo "    Leave empty for a first trial over plain HTTP (insecure cookies, to fix afterwards)."
ask PUBLIC_ORIGIN "HTTPS address" ""
PUBLIC_ORIGIN="${PUBLIC_ORIGIN%/}"
if [ -n "$PUBLIC_ORIGIN" ]; then
  [[ "$PUBLIC_ORIGIN" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || die "Invalid address: $PUBLIC_ORIGIN (e.g. https://mypds.home.example)"
  ask PROXY_IP "Reverse proxy IP (empty to set it later)" ""
fi

echo
say "MyPDS admin account"
ask ADMIN_USER "Username" "admin"
ask ADMIN_NAME "Display name" "$ADMIN_USER"
while :; do
  read -rsp "Password (at least 12 characters): " ADMIN_PASSWORD; echo
  read -rsp "Confirm password: " confirm; echo
  [ "$ADMIN_PASSWORD" = "$confirm" ] || { warn "The passwords don't match."; continue; }
  [ "${#ADMIN_PASSWORD}" -ge 12 ] || { warn "At least 12 characters, please."; continue; }
  break
done
unset confirm

net="name=eth0,bridge=$CT_BRIDGE,firewall=1"
[ -n "$CT_VLAN" ] && net+=",tag=$CT_VLAN"
if [ "$CT_IP" = "dhcp" ]; then net+=",ip=dhcp"; else net+=",ip=$CT_IP,gw=$CT_GW"; fi

echo
say "Summary"
cat <<EOF
    Container  $CTID "$CT_HOSTNAME": $CT_CORES vCPU, $CT_MEMORY_MB MB, $CT_DISK_GB GB disk on $CT_STORAGE
    Network    $net
    Access     ${PUBLIC_ORIGIN:-plain HTTP (trial)}
    Admin      $ADMIN_USER
    Version    $NAME${DEMO:+ (with demo connectors)}
EOF
if [ -t 0 ]; then
  read -rp "Create the container and install? [y/N]: " go
  [[ "$go" =~ ^[yYoO]$ ]] || die "Cancelled: nothing was created."
fi

# ---------- Debian 13 template ----------
say "Debian 13 template"
tpl_storage="$(pvesm status -content vztmpl 2>/dev/null | awk 'NR>1 && $3=="active" {print $1; exit}')"
[ -n "$tpl_storage" ] || die "No storage accepts container templates (\"vztmpl\" content)."
template="$(pveam list "$tpl_storage" 2>/dev/null | awk '{print $1}' | grep -m1 'debian-13-standard' || true)"
if [ -z "$template" ]; then
  pveam update >/dev/null
  latest="$(pveam available --section system | awk '{print $2}' | grep '^debian-13-standard' | sort -V | tail -1)"
  [ -n "$latest" ] || die "Template debian-13-standard not found in the Proxmox catalog."
  say "Downloading $latest"
  pveam download "$tpl_storage" "$latest" >/dev/null
  template="$tpl_storage:vztmpl/$latest"
fi

# ---------- Container ----------
say "Creating container $CTID"
pct create "$CTID" "$template" \
  --hostname "$CT_HOSTNAME" \
  --unprivileged 1 \
  --features nesting=1 \
  --cores "$CT_CORES" --memory "$CT_MEMORY_MB" --swap "$CT_SWAP_MB" \
  --rootfs "$CT_STORAGE:$CT_DISK_GB" \
  --net0 "$net" \
  --onboot "${CT_ONBOOT:-1}" \
  --tags "${CT_TAGS:-mypds}" \
  --description "My Personal Digital Space" >/dev/null
pct start "$CTID"

say "Waiting for the network"
ip=""
for _ in $(seq 1 60); do
  ip="$(pct exec "$CTID" -- sh -c "ip -4 -o addr show dev eth0 2>/dev/null | awk '{print \$4}' | cut -d/ -f1 | head -1" || true)"
  if [ -n "$ip" ] && pct exec "$CTID" -- sh -c 'getent hosts deb.debian.org >/dev/null'; then break; fi
  sleep 2
done
[ -n "$ip" ] || die "The container got no address (VLAN ${CT_VLAN:-none}, DHCP?). It was left in place: pct enter $CTID to investigate, pct destroy $CTID to start over."
pct exec "$CTID" -- sh -c 'getent hosts deb.debian.org >/dev/null' || die "No Internet or DNS access from the container ($ip): Debian packages can't be installed."
say "Container address: $ip"

# ---------- Installation ----------
say "Copying MyPDS"
pct push "$CTID" "$ARCHIVE" "/root/$NAME.tar.gz"
pct exec "$CTID" -- tar -C /root -xzf "/root/$NAME.tar.gz"

say "Installing (Debian packages, database, service): this takes a few minutes"
pct exec "$CTID" -- env MYPDS_NO_ADMIN_PROMPT=1 "/root/$NAME/deploy/install.sh"

say "Configuring access"
envf=/etc/mypds/mypds.env
if [ -n "$PUBLIC_ORIGIN" ]; then
  pct exec "$CTID" -- sed -i "s|^# MYPDS_PUBLIC_ORIGIN=.*|MYPDS_PUBLIC_ORIGIN=$PUBLIC_ORIGIN|" "$envf"
  if [ -n "${PROXY_IP:-}" ]; then
    pct exec "$CTID" -- sed -i "s|^MYPDS_TRUSTED_PROXIES=.*|MYPDS_TRUSTED_PROXIES='[\"$PROXY_IP/32\"]'|" "$envf"
  fi
else
  # Plain HTTP trial: browsers refuse "Secure" cookies without HTTPS
  pct exec "$CTID" -- sed -i 's|^MYPDS_COOKIE_SECURE=.*|MYPDS_COOKIE_SECURE=false|' "$envf"
fi
pct exec "$CTID" -- systemctl restart mypds.service

mypds_cli() { # runs the MyPDS CLI in the container, as the service user, with its configuration
  # shellcheck disable=SC2016  # expanded inside the container
  pct exec "$CTID" -- runuser -u mypds -- bash -c 'set -a; . /etc/mypds/mypds.env; set +a; exec /opt/mypds/current/venv/bin/mypds "$@"' _ "$@"
}

say "Admin account"
printf '%s\n' "$ADMIN_PASSWORD" | mypds_cli create-user "$ADMIN_USER" --display-name "$ADMIN_NAME" --role admin --password-stdin
unset ADMIN_PASSWORD
pct exec "$CTID" -- rm -rf "/root/$NAME" "/root/$NAME.tar.gz"

if [ "${DEMO:-0}" = 1 ]; then
  say "Demo connectors"
  mypds_cli demo
fi

say "Checks"
ready=0
for _ in $(seq 1 30); do
  if pct exec "$CTID" -- curl -fsS -o /dev/null http://127.0.0.1:8080/readyz; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || die "The service does not answer: pct exec $CTID -- journalctl -u mypds -n 50"
mypds_cli doctor || die "\"mypds doctor\" reported a problem (see above)."

echo
say "MyPDS is installed in container $CTID ($ip)."
if [ -n "$PUBLIC_ORIGIN" ]; then
  cat <<EOF
    1. In your reverse proxy: ${PUBLIC_ORIGIN#https://} → http://$ip:8080
       (with Nginx Proxy Manager: Block Common Exploits, certificate, Force SSL, HSTS).
    2. Open $PUBLIC_ORIGIN and sign in as "$ADMIN_USER".
EOF
  [ -n "${PROXY_IP:-}" ] || warn "Set your reverse proxy's IP in /etc/mypds/mypds.env (MYPDS_TRUSTED_PROXIES), then: systemctl restart mypds"
  if [ "$CT_IP" = "dhcp" ]; then warn "The address comes from DHCP: reserve $ip on your router so it doesn't change."; fi
else
  cat <<EOF
    Trial: open http://$ip:8080 and sign in as "$ADMIN_USER".
EOF
  warn "Plain HTTP trial: before real use, put MyPDS behind HTTPS and set"
  warn "MYPDS_COOKIE_SECURE=true and MYPDS_PUBLIC_ORIGIN in /etc/mypds/mypds.env (pct enter $CTID)."
fi
warn "Save the container's encryption key /etc/mypds/secret.key in your password manager:"
warn "  pct exec $CTID -- base64 /etc/mypds/secret.key"
