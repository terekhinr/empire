#!/bin/sh
# USB-диск: mount + Samba (\\flint\\download) + Transmission с сохранением данных.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[usb]\033[0m %s\n' "$*"; }

MNT=/mnt/usb
SHARE=download
# Keenetic часто: \\Keenetic\\download — на Flint: \\192.168.1.1\\download

opkg update || true
opkg install block-mount kmod-fs-ext4 kmod-fs-ntfs3 kmod-fs-vfat ntfs-3g \
  kmod-usb-storage kmod-usb2 kmod-usb3 \
  samba4-server transmission-daemon 2>/dev/null || true

block detect >/dev/null 2>&1 || true
sleep 2

DEV=""
for d in /dev/sd*[0-9]; do
  [ -b "$d" ] || continue
  FSTYPE="$(blkid -s TYPE -o value "$d" 2>/dev/null || true)"
  case "$FSTYPE" in ntfs|ext4|ext3|vfat|exfat) DEV="$d"; break ;; esac
done

if [ -z "$DEV" ]; then
  log "USB не найден — вставьте диск и запустите снова"
  exit 1
fi

UUID="$(blkid -s UUID -o value "$DEV" 2>/dev/null || true)"
FSTYPE="$(blkid -s TYPE -o value "$DEV" 2>/dev/null || echo ext4)"
MNT_FSTYPE="$FSTYPE"
[ "$FSTYPE" = ntfs ] && MNT_FSTYPE="ntfs-3g"
mkdir -p "$MNT"

if [ -n "$UUID" ]; then
  grep -q "$UUID" /etc/fstab || echo "UUID=$UUID $MNT $MNT_FSTYPE defaults,nofail 0 0" >> /etc/fstab
else
  grep -q "$DEV" /etc/fstab || echo "$DEV $MNT $MNT_FSTYPE defaults,nofail 0 0" >> /etc/fstab
fi

mount "$MNT" 2>/dev/null || mount -t "$MNT_FSTYPE" -o rw "$DEV" "$MNT"

# Сохранить структуру с Keenetic: ищем существующие downloads / transmission
DL="$MNT/download"
for cand in "$MNT/downloads" "$MNT/Download" "$MNT/transmission" "$MNT"; do
  if [ -d "$cand" ] && [ -n "$(ls -A "$cand" 2>/dev/null)" ]; then
    DL="$cand"
    break
  fi
done
mkdir -p "$DL"

# Transmission: подхватить settings.json если уже на диске (с Keenetic/старого setup)
T_SETTINGS=""
for s in "$MNT/transmission/settings.json" "$DL/settings.json" "$MNT/.config/transmission-daemon/settings.json"; do
  if [ -f "$s" ]; then T_SETTINGS="$s"; break; fi
done

uci -q set transmission.transmission=transmission 2>/dev/null || true
uci set transmission.transmission.enabled='1'
uci set transmission.transmission.download_dir="$DL"
uci set transmission.transmission.incomplete_dir="$DL/.incomplete"
uci set transmission.transmission.incomplete_dir_enabled='1'
uci set transmission.transmission.config_dir='/etc/transmission/config'
mkdir -p /etc/transmission/config

if [ -n "$T_SETTINGS" ]; then
  log "найден settings.json на диске — копирую (сохраняем торренты)"
  cp -a "$T_SETTINGS" /etc/transmission/config/settings.json
  # поправить путь загрузки на актуальный
  sed -i "s|\"download-dir\".*|\"download-dir\": \"$DL\",|" /etc/transmission/config/settings.json 2>/dev/null || true
fi

uci set transmission.transmission.rpc_enabled='1'
uci set transmission.transmission.rpc_whitelist_enabled='0'
uci commit transmission

# Samba — сетевой диск как на Keenetic
uci -q set samba4=samba 2>/dev/null || true
uci set samba4.@samba[0].name='FLINT'
uci set samba4.@samba[0].workgroup='HOME'
uci set samba4.@samba[0].charset='UTF-8'

uci -q delete samba4.$SHARE 2>/dev/null || true
uci set samba4.$SHARE=sambashare
uci set samba4.$SHARE.name="$SHARE"
uci set samba4.$SHARE.path="$DL"
uci set samba4.$SHARE.read_only='no'
uci set samba4.$SHARE.guest_ok='yes'
uci set samba4.$SHARE.create_mask='0664'
uci set samba4.$SHARE.dir_mask='0775'
uci commit samba4

# Transmission: постоянно (расписание отключено — Flint 2 тянет 24/7)
# Ранее Keenetic: 01:00–05:59 MSK. Раскомментируйте cron ниже, если нужно вернуть окно.
# curl -fsSL "$BASE/transmission-schedule.sh" -o /etc/transmission-schedule.sh 2>/dev/null || true
# chmod +x /etc/transmission-schedule.sh 2>/dev/null || true
# ( crontab -l 2>/dev/null | grep -v transmission-schedule
#   echo "0 1 * * * /etc/transmission-schedule.sh start"
#   echo "0 6 * * * /etc/transmission-schedule.sh stop"
#   echo "*/10 * * * * /etc/transmission-schedule.sh"
# ) | crontab - 2>/dev/null || true

/etc/init.d/samba4 enable
/etc/init.d/samba4 restart
/etc/init.d/transmission enable
/etc/init.d/transmission restart 2>/dev/null || /etc/init.d/transmission start

log "USB: $DEV → $MNT"
log "Samba: \\\\192.168.1.1\\$SHARE  (Total Commander: \\\\flint\\$SHARE)"
log "Transmission: $DL (24/7)"
log "Контент на диске сохранён — тот же UUID, те же файлы"
