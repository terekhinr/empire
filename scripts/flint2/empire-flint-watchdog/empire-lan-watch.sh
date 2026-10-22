#!/bin/sh
# Dedupe sing-box + empire-singbox-patch. БЕЗ podkop restart.
# USB/Samba keep-alive + LKG restore если FakeIP/AI сломан.
# Запуск только под flock (cron: flock -n /var/lock/empire-heal.lock ...).
set -eu

LOCK=/var/lock/empire-heal.lock
if [ -z "${EMPIRE_HEAL_LOCKED:-}" ]; then
  exec flock -n "$LOCK" env EMPIRE_HEAL_LOCKED=1 "$0" "$@"
fi

# --- USB + Samba (лёгкая проверка каждую минуту; не зависит от podkop) ---
USB_UUID="01D63D133C7B6100"
usb_ok=0
line=$(grep ' /mnt/usb ' /proc/mounts 2>/dev/null | tail -1 || true)
if [ -n "$line" ] && echo "$line" | grep -qE 'fuseblk|ntfs' && ! echo "$line" | grep -q ' ext3 '; then
  dev=$(echo "$line" | awk '{print $1}')
  uuid=$(blkid -s UUID -o value "$dev" 2>/dev/null || true)
  if [ "$uuid" = "$USB_UUID" ] && [ -d /mnt/usb/download ] && touch /mnt/usb/download/.empire_usb_ok 2>/dev/null; then
    usb_ok=1
  fi
fi
if [ "$usb_ok" != "1" ]; then
  [ -x /etc/init.d/empire-usb-mount ] && /etc/init.d/empire-usb-mount start >/dev/null 2>&1 || true
fi
# Samba: процесс + шара download на /mnt/usb/download
samba_need=0
pgrep -f 'smbd|samba' >/dev/null 2>&1 || samba_need=1
sp=$(uci -q get samba4.download.path 2>/dev/null || true)
[ "$sp" = "/mnt/usb/download" ] || samba_need=1
if [ "$samba_need" = "1" ]; then
  DL="/mnt/usb/download"
  mkdir -p "$DL" 2>/dev/null || true
  if [ "$(uci -q get samba4.download.path 2>/dev/null || true)" != "$DL" ]; then
    uci -q set samba4.download=sambashare 2>/dev/null || true
    uci -q set samba4.download.name='download' 2>/dev/null || true
    uci -q set samba4.download.path="$DL" 2>/dev/null || true
    uci -q set samba4.download.read_only='no' 2>/dev/null || true
    uci -q set samba4.download.guest_ok='yes' 2>/dev/null || true
    uci commit samba4 2>/dev/null || true
  fi
  /etc/init.d/samba4 start >/dev/null 2>&1 || /etc/init.d/samba start >/dev/null 2>&1 || true
  /etc/init.d/samba4 reload >/dev/null 2>&1 || /etc/init.d/samba4 restart >/dev/null 2>&1 || true
fi

# --- sing-box: LKG, не podkop start (иначе race → duplicate rule-set) ---
if ! pgrep -f '/usr/bin/sing-box run' >/dev/null 2>&1; then
  if [ -x /usr/sbin/empire-singbox-lkg ]; then
    /usr/sbin/empire-singbox-lkg restore >/dev/null 2>&1 || true
  else
    /etc/init.d/sing-box start >/dev/null 2>&1 || true
  fi
  exit 0
fi

keep=""; n=0
for p in $(pgrep -f '/usr/bin/sing-box run' 2>/dev/null); do
  n=$((n + 1))
  [ "$n" -eq 1 ] && keep=$p && continue
  kill "$p" 2>/dev/null || true
done

[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch

if [ -f /etc/podkop/telegram-subnets.lst ]; then
  while read -r cidr; do
    echo "$cidr" | grep -qE '^[0-9]' || continue
    nft add element inet PodkopTable podkop_subnets "{ $cidr }" 2>/dev/null || true
  done < /etc/podkop/telegram-subnets.lst
fi

# --- AI/TG FakeIP keep-alive: только LKG restore, без 36-ai/podkop restart ---
need_lkg=0
cip=$(nslookup api2.cursor.sh 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$cip" in
  198.18.*) ;;
  *) need_lkg=1 ;;
esac
tip=$(nslookup telegram.org 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
case "$tip" in
  198.18.*) ;;
  *) need_lkg=1 ;;
esac
if ! grep -q 'ai_awg-user-domains-ruleset' /etc/sing-box/config.json 2>/dev/null; then
  need_lkg=1
fi

if [ "$need_lkg" = "1" ] && [ -x /usr/sbin/empire-singbox-lkg ]; then
  now=$(date +%s)
  last=0
  [ -f /tmp/empire-ai-fix.ts ] && last=$(cat /tmp/empire-ai-fix.ts 2>/dev/null || echo 0)
  if [ $((now - last)) -ge 180 ]; then
    echo "$now" >/tmp/empire-ai-fix.ts
    /usr/sbin/empire-singbox-lkg restore >/tmp/empire-ai-fix.out 2>&1 || true
  fi
fi

# AI DNS must stay on FakeIP/awg0
/etc/empire/empire-dns-ai-tunnel.sh >/dev/null 2>&1 || true
