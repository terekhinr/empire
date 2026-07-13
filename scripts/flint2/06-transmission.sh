#!/bin/sh
# Transmission + ночное окно 01:00–05:59 MSK (как на Keenetic).
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[transmission]\033[0m %s\n' "$*"; }

opkg update || true
opkg install transmission-daemon 2>/dev/null || opkg install transmission-daemon-openssl 2>/dev/null || true

DL="/mnt/usb/downloads"
mkdir -p "$DL" 2>/dev/null || DL="/root/downloads"
mkdir -p "$DL"

uci -q set transmission.@transmission[0].enabled='1' 2>/dev/null || true
uci set transmission.@transmission[0].download_dir="$DL" 2>/dev/null || true
uci set transmission.@transmission[0].rpc_whitelist_enabled='0' 2>/dev/null || true
uci commit transmission 2>/dev/null || true

curl -fL -o /etc/transmission-schedule.sh "$BASE/transmission-schedule.sh" 2>/dev/null || \
  curl -fL -o /etc/transmission-schedule.sh "$BASE/../keenetic-xkeen/transmission-schedule.sh" 2>/dev/null || true
chmod +x /etc/transmission-schedule.sh 2>/dev/null || true

( crontab -l 2>/dev/null | grep -v transmission-schedule
  echo "*/5 * * * * /etc/transmission-schedule.sh"
) | crontab - 2>/dev/null || true

/etc/init.d/transmission enable 2>/dev/null || true
log "transmission: $DL (USB → /mnt/usb)"
