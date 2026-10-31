#!/bin/sh
# Восстановить список торрентов Transmission с USB (после миграции с Keenetic).
set -eu

CFG=/etc/transmission/config
DL=/mnt/usb/download

log() { printf '\033[1;32m[transmission-restore]\033[0m %s\n' "$*"; }

[ -d /mnt/usb/torrents ] || { log "нет /mnt/usb/torrents — вставьте USB"; exit 1; }

log "остановка transmission"
/etc/init.d/transmission stop
sleep 2

mkdir -p "$CFG/torrents" "$CFG/resume"

log "копирую torrents и resume"
cp -a /mnt/usb/torrents/* "$CFG/torrents/"
[ -d /mnt/usb/resume ] && cp -a /mnt/usb/resume/* "$CFG/resume/" || true
[ -d /mnt/usb/found.000/dir0000.chk ] && cp -n /mnt/usb/found.000/dir0000.chk/*.resume "$CFG/resume/" 2>/dev/null || true

if [ -f /mnt/usb/settings.json ]; then
  log "settings.json с USB + правка путей"
  cp -a /mnt/usb/settings.json "$CFG/settings.json"
  sed -i "s|/tmp/mnt/[^\"]*/download|$DL|g" "$CFG/settings.json"
  sed -i 's/"rpc-port": 8090/"rpc-port": 9091/g' "$CFG/settings.json"
  sed -i 's/"rpc-authentication-required": true/"rpc-authentication-required": false/g' "$CFG/settings.json"
  sed -i 's/"rpc-host-whitelist-enabled": true/"rpc-host-whitelist-enabled": false/g' "$CFG/settings.json"
  sed -i 's/"rpc-whitelist-enabled": true/"rpc-whitelist-enabled": false/g' "$CFG/settings.json"
  sed -i "s|\"download-dir\": \"[^\"]*\"|\"download-dir\": \"$DL\"|g" "$CFG/settings.json"
  sed -i "s|\"incomplete-dir\": \"[^\"]*\"|\"incomplete-dir\": \"$DL/.incomplete\"|g" "$CFG/settings.json"
  sed -i 's/"incomplete-dir-enabled": false/"incomplete-dir-enabled": true/g' "$CFG/settings.json"
fi

[ -f /mnt/usb/dht.dat ] && cp -a /mnt/usb/dht.dat "$CFG/" || true
[ -f /mnt/usb/bandwidth.json ] && cp -a /mnt/usb/bandwidth.json "$CFG/" || true

# В .resume остаётся destination Keenetic — без замены «No data found»
OLD="/tmp/mnt/01D63D133C7B6100/download"
OLD_DEST="destination34:${OLD}"
NEW_DEST="destination17:${DL}"
for f in "$CFG/resume"/*.resume; do
  [ -f "$f" ] || continue
  sed -i "s|${OLD_DEST}|${NEW_DEST}|g" "$f"
  sed -i "s|${OLD}|${DL}|g" "$f"
  sed -i "s|destination[0-9]*:/tmp/mnt/[^/]*/download|${NEW_DEST}|g" "$f"
done

chown -R transmission:transmission "$CFG"

uci set transmission.@transmission[0].enabled='1'
uci set transmission.@transmission[0].config_dir="$CFG"
uci set transmission.@transmission[0].config_overwrite='0'
uci set transmission.@transmission[0].download_dir="$DL"
uci set transmission.@transmission[0].incomplete_dir="$DL/.incomplete"
uci set transmission.@transmission[0].incomplete_dir_enabled='1'
uci set transmission.@transmission[0].rpc_enabled='1'
uci set transmission.@transmission[0].rpc_whitelist_enabled='0'
uci -q delete transmission.transmission 2>/dev/null || true
uci commit transmission

log "запуск transmission"
/etc/init.d/transmission start

log "torrents: $(ls "$CFG/torrents" | wc -l), resume: $(ls "$CFG/resume" | wc -l)"
log "Remote GUI: 192.168.1.1:9091 (без пароля)"
