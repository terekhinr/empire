#!/bin/sh
# Reverse SSH: Flint 2 (22) → VPS (127.0.0.1:6223). Агент настраивает роутер с VPS.
# curl -fsSL http://193.233.232.48:8789/07-router-tunnel.sh | sh
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
VPS="${FLINT2_VPS:-193.233.232.48}"
VPS_PORT=22
TUN_LOCAL=6223
ROUTER_SSH=22
KEY_DIR=/etc/flint2-tunnel
KEY="$KEY_DIR/id_ed25519"
REGISTER_TOKEN="***REMOVED***"

log() { printf '\033[1;32m[tunnel]\033[0m %s\n' "$*"; }

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

opkg update || true
opkg install openssh-client openssh-keygen 2>/dev/null || opkg install openssh-client 2>/dev/null || true

if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -N "" -f "$KEY" -C "flint2-router-tunnel"
fi
PUB="$(cat "${KEY}.pub")"

curl -fsS -X POST "$BASE/register-router-key" \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$REGISTER_TOKEN\",\"pubkey\":\"$PUB\"}" \
  || log "WARN: register (возможно уже зарегистрирован)"

kill "$(pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ROUTER_SSH}.*${VPS}" 2>/dev/null)" 2>/dev/null || true

SSH_OPTS="-y -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes"

ssh -f -N $SSH_OPTS -i "$KEY" \
  -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ROUTER_SSH}" \
  "root@${VPS}" -p "$VPS_PORT"

cat > "$KEY_DIR/start.sh" << EOF
#!/bin/sh
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:\$PATH"
VPS="${VPS}"
TUN_LOCAL=${TUN_LOCAL}
ROUTER_SSH=${ROUTER_SSH}
KEY="${KEY}"
kill "\$(pgrep -f "ssh.*-R 127.0.0.1:\${TUN_LOCAL}:127.0.0.1:\${ROUTER_SSH}.*\${VPS}" 2>/dev/null)" 2>/dev/null || true
sleep 2
ssh -f -N -y -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \\
  -i "\$KEY" -R "127.0.0.1:\${TUN_LOCAL}:127.0.0.1:\${ROUTER_SSH}" "root@\${VPS}"
EOF
chmod +x "$KEY_DIR/start.sh"

( crontab -l 2>/dev/null | grep -v flint2-tunnel/start
  echo "*/10 * * * * $KEY_DIR/start.sh"
) | crontab - 2>/dev/null || true

log "VPS: ssh -p ${TUN_LOCAL} root@127.0.0.1"
pgrep -fa "ssh.*${VPS}" || log "туннель не найден — проверьте WAN и ключ на VPS"
