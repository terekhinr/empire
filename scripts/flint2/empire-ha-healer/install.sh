#!/bin/bash
# Установка empire-ha-healer на Flint.
# Скрипт качается с VPS bootstrap http://193.233.232.48:8789/empire-ha-healer/
# SSH: FLINT_ADMIN_PASSWORD из /root/.flint-admin.env (или :6223).
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
EMPIRE_ROOT="$(cd "$ROOT/../../.." && pwd)"
BOOTSTRAP="${EMPIRE_HA_HEALER_BOOTSTRAP:-http://193.233.232.48:8789/empire-ha-healer}"

set -a
# shellcheck disable=SC1091
[ -f "$EMPIRE_ROOT/.env" ] && . "$EMPIRE_ROOT/.env"
# shellcheck disable=SC1091
[ -f /root/.flint-admin.env ] && . /root/.flint-admin.env
set +a

HA_TOKEN="${HA_TOKEN:?HA_TOKEN missing}"
PASS="${FLINT_ADMIN_PASSWORD:-}"

remote() {
  if [ -n "$PASS" ] && command -v sshpass >/dev/null 2>&1; then
    SSHPASS="$PASS" sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 root@192.168.1.1 "$@"
    return
  fi
  if ssh -p 6223 -o BatchMode=yes -o ConnectTimeout=8 root@127.0.0.1 'true' 2>/dev/null; then
    ssh -p 6223 -o BatchMode=yes -o ConnectTimeout=20 root@127.0.0.1 "$@"
    return
  fi
  echo "FAIL: нет SSH на Flint (пароль или :6223). На роутере: sh install-local.sh"
  exit 1
}

echo "==> install from $BOOTSTRAP"
remote "HA_TOKEN=$(printf %q "$HA_TOKEN") BOOTSTRAP=$(printf %q "$BOOTSTRAP") sh -s" <<'EOF'
set -eu
curl -fsSL "$BOOTSTRAP/empire-ha-healer" -o /usr/sbin/empire-ha-healer
curl -fsSL "$BOOTSTRAP/empire-ha-healer.init" -o /etc/init.d/empire-ha-healer
chmod 755 /usr/sbin/empire-ha-healer /etc/init.d/empire-ha-healer
sed -i 's/\r$//' /usr/sbin/empire-ha-healer /etc/init.d/empire-ha-healer
if [ -f /etc/empire-flint-ui.env ]; then
  grep -vE '^(HA_URL|HA_TOKEN)=' /etc/empire-flint-ui.env > /tmp/efe.env || true
else
  : > /tmp/efe.env
fi
printf '%s\n' 'HA_URL=http://192.168.1.41:8123' "HA_TOKEN=$HA_TOKEN" >> /tmp/efe.env
mv /tmp/efe.env /etc/empire-flint-ui.env
chmod 600 /etc/empire-flint-ui.env
[ -f /etc/empire-ha-healer.env ] || printf '%s\n' '# STUCK_OCCUPANCY_SEC=2700' '# DESYNC_LIGHT_SEC=180' > /etc/empire-ha-healer.env
CRON_FILE=/etc/crontabs/root
mkdir -p /etc/crontabs
touch "$CRON_FILE"
grep -v 'empire-ha-healer' "$CRON_FILE" >"${CRON_FILE}.tmp" || true
mv "${CRON_FILE}.tmp" "$CRON_FILE"
echo '*/5 * * * * /usr/sbin/empire-ha-healer >/dev/null 2>&1' >>"$CRON_FILE"
/etc/init.d/cron enable 2>/dev/null || true
/etc/init.d/cron restart 2>/dev/null || true
ln -sf /etc/init.d/empire-ha-healer /etc/rc.d/S99empire-ha-healer 2>/dev/null || true
EMPIRE_HA_HEAL_VERBOSE=1 /usr/sbin/empire-ha-healer --check || true
echo OK
EOF
