#!/bin/sh
# Локальная установка на самом Flint (USB / уже на роутере).
set -eu
cd "$(dirname "$0")"
cp -a empire-ha-healer /usr/sbin/empire-ha-healer
chmod 755 /usr/sbin/empire-ha-healer
sed -i 's/\r$//' /usr/sbin/empire-ha-healer
cp -a empire-ha-healer.init /etc/init.d/empire-ha-healer
chmod 755 /etc/init.d/empire-ha-healer
sed -i 's/\r$//' /etc/init.d/empire-ha-healer
[ -f /etc/empire-flint-ui.env ] || echo "HA_URL=http://192.168.1.41:8123" >/etc/empire-flint-ui.env
[ -f /etc/empire-ha-healer.env ] || cat >/etc/empire-ha-healer.env <<'EOF'
# STUCK_OCCUPANCY_SEC=2700
# DESYNC_LIGHT_SEC=180
EOF
/etc/init.d/empire-ha-healer enable 2>/dev/null || true
/etc/init.d/empire-ha-healer start
EMPIRE_HA_HEAL_VERBOSE=1 /usr/sbin/empire-ha-healer --check || true
echo "OK — cron */5 empire-ha-healer"
