#!/bin/sh
# Установка сторожа НА самом Flint (USB / скопированный каталог). VPS не нужен.
# Запуск: sh install-local.sh   из каталога empire-flint-watchdog/
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"

log() { printf '\033[1;32m[wd-local]\033[0m %s\n' "$*"; }

if [ ! -f /etc/openwrt_release ]; then
  echo "Этот скрипт запускается на OpenWrt (Flint), не на VPS."
  echo "С VPS: bash $ROOT/install.sh  (нужен reverse SSH :6223)"
  exit 1
fi

mkdir -p /etc/empire /etc/podkop /etc/crontabs /www/cgi-bin /www/empire \
  /etc/dnsmasq.d /tmp/dnsmasq.d /etc/hotplug.d/block

cp -a "$ROOT/mode-lib.sh" /etc/empire/mode-lib.sh
cp -a "$ROOT/vless-failover.sh" /usr/sbin/empire-vless-failover
cp -a "$ROOT/empire-flint-watchdog" /usr/sbin/empire-flint-watchdog
chmod 755 /etc/empire/mode-lib.sh /usr/sbin/empire-flint-watchdog /usr/sbin/empire-vless-failover
sed -i 's/\r$//' /usr/sbin/empire-flint-watchdog /usr/sbin/empire-vless-failover /etc/empire/mode-lib.sh

cp -a "$ROOT/empire-flint-watchdog.init" /etc/init.d/empire-flint-watchdog
chmod 755 /etc/init.d/empire-flint-watchdog
sed -i 's/\r$//' /etc/init.d/empire-flint-watchdog

cp -a "$ROOT/empire-lan-fix.sh" /etc/podkop/empire-lan-fix.sh
cp -a "$ROOT/empire-lan-watch.sh" /etc/podkop/empire-lan-watch.sh
cp -a "$ROOT/empire-singbox-patch.sh" /usr/sbin/empire-singbox-patch
cp -a "$ROOT/empire-singbox-mark.sh" /usr/sbin/empire-singbox-mark
cp -a "$ROOT/empire-lan-verify.sh" /usr/sbin/empire-lan-verify
cp -a "$ROOT/enforce-vless-ssh.sh" /etc/empire/enforce-vless-ssh.sh
chmod 755 /etc/podkop/empire-lan-fix.sh /etc/podkop/empire-lan-watch.sh \
  /usr/sbin/empire-singbox-patch /usr/sbin/empire-singbox-mark /usr/sbin/empire-lan-verify \
  /etc/empire/enforce-vless-ssh.sh
sed -i 's/\r$//' /etc/podkop/empire-lan-fix.sh /etc/podkop/empire-lan-watch.sh \
  /usr/sbin/empire-singbox-patch /usr/sbin/empire-singbox-mark /usr/sbin/empire-lan-verify \
  /etc/empire/enforce-vless-ssh.sh

grep -q empire-singbox-mark /etc/init.d/sing-box 2>/dev/null || \
  sed -i "/procd_open_instance/i\\
\t[ -x /usr/sbin/empire-singbox-mark ] \&\& /usr/sbin/empire-singbox-mark\\
" /etc/init.d/sing-box 2>/dev/null || true

if [ -f "$ROOT/../torrent-domains.txt" ]; then
  cp -a "$ROOT/../torrent-domains.txt" /etc/podkop/torrent-domains.txt
fi
if [ -f "$ROOT/../zapret-hosts.txt" ]; then
  cp -a "$ROOT/../zapret-hosts.txt" /etc/podkop/zapret-hosts.txt
fi
cp -a "$ROOT/block-doh.nft" /etc/podkop/block-doh.nft
cp -a "$ROOT/99-block-doh.conf" /etc/dnsmasq.d/99-block-doh.conf
cp -a /etc/dnsmasq.d/99-block-doh.conf /tmp/dnsmasq.d/99-block-doh.conf 2>/dev/null || true
sed -i 's/\r$//' /etc/podkop/block-doh.nft /etc/dnsmasq.d/99-block-doh.conf

if [ -f "$ROOT/empire-usb-mount.init" ]; then
  cp -a "$ROOT/empire-usb-mount.init" /etc/init.d/empire-usb-mount
  chmod 755 /etc/init.d/empire-usb-mount
  /etc/init.d/empire-usb-mount enable 2>/dev/null || true
fi
if [ -f "$ROOT/hotplug-20-empire-usb" ]; then
  cp -a "$ROOT/hotplug-20-empire-usb" /etc/hotplug.d/block/20-empire-usb
  chmod 755 /etc/hotplug.d/block/20-empire-usb
fi

cp -a "$ROOT/cgi/empire-api" /www/cgi-bin/empire-api
chmod 755 /www/cgi-bin/empire-api
sed -i 's/\r$//' /www/cgi-bin/empire-api
if [ -d "$ROOT/www" ]; then
  cp -a "$ROOT/www/." /www/empire/
fi

if [ ! -f /etc/empire-flint-ui.token ]; then
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16 >/etc/empire-flint-ui.token
  else
    tr -dc 'a-f0-9' </dev/urandom | head -c 32 >/etc/empire-flint-ui.token
  fi
  chmod 600 /etc/empire-flint-ui.token
  log "токен создан: /etc/empire-flint-ui.token"
fi
[ -f /etc/empire-flint-ui.env ] || echo "HA_URL=http://192.168.1.41:8123" >/etc/empire-flint-ui.env
chmod 600 /etc/empire-flint-ui.env

uci set uhttpd.main.cgi_prefix='/cgi-bin'
uci set uhttpd.main.home='/www'
uci set uhttpd.main.rfc1918_filter='0'
uci commit uhttpd
/etc/init.d/uhttpd restart 2>/dev/null || true

mkdir -p /etc/crontabs
if [ -x /usr/sbin/empire-cron-normalize ]; then
  /usr/sbin/empire-cron-normalize
else
  CRON_FILE=/etc/crontabs/root
  grep -vE 'empire-flint-watchdog|empire-lan-watch' "$CRON_FILE" >"${CRON_FILE}.tmp" 2>/dev/null || true
  mv "${CRON_FILE}.tmp" "$CRON_FILE" 2>/dev/null || : >"$CRON_FILE"
  echo '* * * * * flock -n /var/lock/empire-heal.lock /etc/podkop/empire-lan-watch.sh' >>"$CRON_FILE"
  echo '*/5 * * * * flock -n /var/lock/empire-heal.lock /usr/sbin/empire-flint-watchdog >/dev/null 2>&1' >>"$CRON_FILE"
  /etc/init.d/cron restart 2>/dev/null || true
fi
/etc/init.d/cron enable 2>/dev/null || true
/etc/init.d/empire-flint-watchdog enable 2>/dev/null || true

[ -f /etc/empire/bypass-mode ] || echo vps >/etc/empire/bypass-mode

log "PWA: http://192.168.1.1/empire/?token=$(tr -d '\r\n' </etc/empire-flint-ui.token)"
log "проверка: /usr/sbin/empire-flint-watchdog --check"
/usr/sbin/empire-flint-watchdog --check || true
