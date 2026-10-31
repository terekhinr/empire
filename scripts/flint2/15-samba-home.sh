#!/bin/sh
# Samba: workgroup HOME (как Keenetic), wsdd для Windows, шар download.
set -eu

log() { printf '\033[1;32m[samba]\033[0m %s\n' "$*"; }

opkg update >/dev/null 2>&1 || true
opkg install samba4-server wsdd2 2>/dev/null || true

DL="${SAMBA_PATH:-/mnt/usb/download}"
[ -d "$DL" ] || DL="/mnt/usb/download"
mkdir -p "$DL"

uci -q set samba4=samba 2>/dev/null || true
uci set samba4.@samba[0].name='FLINT'
uci set samba4.@samba[0].workgroup='HOME'
uci set samba4.@samba[0].charset='UTF-8'
uci set samba4.@samba[0].description='Flint download'
# io_uring ломает Windows SMB; Windows 10+ не берёт гостевой вход
uci set samba4.@samba[0].disable_async_io='1'

uci -q delete samba4.download 2>/dev/null || true
uci set samba4.download=sambashare
uci set samba4.download.name='download'
uci set samba4.download.path="$DL"
uci set samba4.download.read_only='no'
uci set samba4.download.guest_ok='yes'
uci set samba4.download.create_mask='0664'
uci set samba4.download.dir_mask='0775'
uci commit samba4

# Windows шлёт имя ПК-пользователя → Bad User → guest → клиент Windows отваливается.
# Never: Windows покажет логин. Анонимный гость (ТВ) с guest_ok всё ещё работает.
if [ -f /etc/samba/smb.conf.template ]; then
  sed -i 's/map to guest = Bad User/map to guest = Never/' /etc/samba/smb.conf.template
fi

if ! grep -q '^home:' /etc/passwd; then
  echo 'home:x:1000:65534:samba:/var:/bin/false' >> /etc/passwd
fi
if command -v smbpasswd >/dev/null 2>&1; then
  printf '%s\n%s\n' home home | smbpasswd -s -a home >/dev/null 2>&1 || true
fi

/etc/init.d/wsdd2 enable 2>/dev/null || true
/etc/init.d/wsdd2 start 2>/dev/null || true
/etc/init.d/samba4 enable
/etc/init.d/samba4 restart

log "Samba: \\\\192.168.1.1\\download  workgroup=HOME"
log "Windows: Win+R → \\\\192.168.1.1\\download"
log "Логин home / пароль home  (не ждать обзора Сеть, Amnezia на ПК выключить)"
