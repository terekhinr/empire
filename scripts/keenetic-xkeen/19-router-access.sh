#!/bin/sh
# Reverse SSH: Entware (222) -> VPS (127.0.0.1:6222). Роутер сам стучится наружу.
# curl -fsSL http://193.233.232.48:8787/19-router-access.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
VPS="${KEENETIC_VPS:-193.233.232.48}"
VPS_PORT=22
TUN_LOCAL=6222
ENTWARE_SSH=222
KEY_DIR=/opt/etc/keenetic-tunnel
KEY=$KEY_DIR/id_ed25519
# Тот же канал, что и для XKeen bootstrap (8787)
REGISTER_TOKEN="***REMOVED***"

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -N "" -f "$KEY" -C "keenetic-router-tunnel"
fi
PUB=$(cat "${KEY}.pub")

# Регистрация ключа на VPS (один POST)
curl -fsS -X POST "$BASE/register-router-key" \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$REGISTER_TOKEN\",\"pubkey\":\"$PUB\"}" \
  || echo "WARN: register failed (maybe already registered)"

# Убить старый туннель
kill $(pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}.*${VPS}") 2>/dev/null || true

SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes"

if command -v autossh >/dev/null 2>&1; then
  autossh -M 0 -f -N $SSH_OPTS -i "$KEY" \
    -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}" \
    "root@${VPS}" -p "$VPS_PORT"
else
  ssh -f -N $SSH_OPTS -i "$KEY" \
    -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}" \
    "root@${VPS}" -p "$VPS_PORT"
fi

cat > /opt/etc/keenetic-tunnel/start.sh << 'EOF'
#!/bin/sh
export PATH="/opt/bin:/opt/sbin:$PATH"
VPS="__VPS__"
TUN_LOCAL="__TUN__"
ENTWARE_SSH="__ENTWARE__"
KEY=/opt/etc/keenetic-tunnel/id_ed25519
kill $(pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}.*${VPS}") 2>/dev/null || true
sleep 2
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes"
if command -v autossh >/dev/null 2>&1; then
  autossh -M 0 -f -N $SSH_OPTS -i "$KEY" -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}" "root@${VPS}"
else
  ssh -f -N $SSH_OPTS -i "$KEY" -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ENTWARE_SSH}" "root@${VPS}"
fi
EOF
sed -i "s|__VPS__|${VPS}|g; s|__TUN__|${TUN_LOCAL}|g; s|__ENTWARE__|${ENTWARE_SSH}|g" /opt/etc/keenetic-tunnel/start.sh
chmod +x /opt/etc/keenetic-tunnel/start.sh

echo "=== ROUTER ACCESS TUNNEL ==="
pgrep -fa "ssh.*${VPS}" || echo "tunnel process not found"
echo "VPS side: ssh -p ${TUN_LOCAL} root@127.0.0.1  (Entware on router :${ENTWARE_SSH})"
