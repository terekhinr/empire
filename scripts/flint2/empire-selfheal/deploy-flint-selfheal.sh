#!/bin/bash
# Деплой самолечения на Flint (+ установка VPS remote heal).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PKG="$ROOT/scripts/flint2/empire-selfheal"
WD="$ROOT/scripts/flint2/empire-flint-watchdog"
PORT="${EMPIRE_FLINT_REV_PORT:-6223}"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p "$PORT" root@127.0.0.1)

echo "==> upload scripts (tar over ssh, no sftp)"
"${SSH[@]}" 'mkdir -p /tmp/empire-selfheal-deploy'
tar -C "$PKG" -cf - empire-cron-normalize.sh empire-singbox-lkg.sh \
  | "${SSH[@]}" 'tar -C /tmp/empire-selfheal-deploy -xf -'
tar -C "$WD" -cf - empire-lan-watch.sh empire-flint-watchdog \
  | "${SSH[@]}" 'tar -C /tmp/empire-selfheal-deploy -xf -'

"${SSH[@]}" 'sh -s' <<'EOF'
set -e
mkdir -p /usr/sbin /etc/podkop /etc/empire /var/lock
cd /tmp/empire-selfheal-deploy
cp -f empire-cron-normalize.sh /usr/sbin/empire-cron-normalize
cp -f empire-singbox-lkg.sh /usr/sbin/empire-singbox-lkg
cp -f empire-lan-watch.sh /etc/podkop/empire-lan-watch.sh
cp -f empire-flint-watchdog /usr/sbin/empire-flint-watchdog
chmod 755 /usr/sbin/empire-cron-normalize /usr/sbin/empire-singbox-lkg \
  /etc/podkop/empire-lan-watch.sh /usr/sbin/empire-flint-watchdog

/usr/sbin/empire-cron-normalize
killall -q podkop 2>/dev/null || true
/usr/sbin/empire-singbox-lkg restore
sleep 3
if /usr/sbin/empire-singbox-lkg smoke; then
  /usr/sbin/empire-singbox-lkg save || true
  echo SMOKE_OK
else
  echo SMOKE_FAIL
  /usr/sbin/empire-flint-watchdog --force || true
  sleep 4
  /usr/sbin/empire-singbox-lkg smoke && echo SMOKE_OK2 || echo SMOKE_STILL_FAIL
fi
for d in telegram.org youtube.com chatgpt.com api2.cursor.sh; do
  a=$(nslookup "$d" 127.0.0.1 2>&1 | awk '/^Address:/{print $2}' | tail -1)
  echo "$d -> $a"
done
curl -o /dev/null -s -w 'tg %{http_code}\n' --max-time 12 https://web.telegram.org/ || true
curl -o /dev/null -s -w 'yt %{http_code}\n' --max-time 12 https://www.youtube.com/generate_204 || true
wc -l /etc/crontabs/root
EOF

echo "==> install VPS remote heal"
install -m 0755 "$PKG/empire-flint-remote-heal.sh" /usr/local/sbin/empire-flint-remote-heal.sh
install -m 0644 "$ROOT/data/infra/systemd/empire-flint-remote-heal.service" /etc/systemd/system/empire-flint-remote-heal.service
install -m 0644 "$ROOT/data/infra/systemd/empire-flint-remote-heal.timer" /etc/systemd/system/empire-flint-remote-heal.timer
systemctl daemon-reload
systemctl enable --now empire-flint-remote-heal.timer
systemctl start empire-flint-remote-heal.service || true
systemctl status empire-flint-remote-heal.timer --no-pager | head -15

echo "DONE"
