#!/bin/sh
# Срочное восстановление Flint: podkop, USB, Samba, Transmission, Amnezia split, туннель.
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[fix-all]\033[0m %s\n' "$*"; }

# --- 1. Пакеты ---
log "opkg update + пакеты..."
opkg update >/dev/null 2>&1 || true
opkg install block-mount kmod-scsi-core kmod-scsi-generic kmod-usb-storage kmod-usb2 \
  kmod-fs-ext4 kmod-fs-vfat kmod-fs-ntfs3 ntfs3-utils \
  samba4-server transmission-daemon transmission-daemon-openssl \
  dnsmasq-full ip-full iptables-nft 2>/dev/null || true

# dnsmasq-full вместо dnsmasq (nftset для Amnezia split)
if opkg list-installed | grep -q '^dnsmasq-full '; then
  opkg remove dnsmasq 2>/dev/null || true
fi

# --- 2. Podkop ---
log "podkop restart..."
/etc/init.d/podkop enable 2>/dev/null || true
/etc/init.d/podkop restart 2>/dev/null || /etc/init.d/podkop start 2>/dev/null || true
sleep 3

# --- 3. USB ---
log "USB mount..."
MNT=/mnt/usb
mkdir -p "$MNT"
block detect >/dev/null 2>&1 || true
sleep 3

DEV=""
for d in /dev/sd*[0-9]; do
  [ -b "$d" ] || continue
  DEV="$d"
  break
done

if [ -z "$DEV" ]; then
  # попытка rescan
  for h in /sys/class/scsi_host/host*/scan; do
    [ -f "$h" ] && echo '- - -' >"$h" 2>/dev/null || true
  done
  sleep 3
  for d in /dev/sd*[0-9]; do
    [ -b "$d" ] || continue
    DEV="$d"
    break
  done
fi

if [ -n "$DEV" ]; then
  UUID="$(blkid -s UUID -o value "$DEV" 2>/dev/null || true)"
  FSTYPE="$(blkid -s TYPE -o value "$DEV" 2>/dev/null || echo ext4)"
  case "$FSTYPE" in
    ntfs) MNT_OPTS="rw" ;;
    *) MNT_OPTS="rw" ;;
  esac
  if [ -n "$UUID" ]; then
    grep -q "$UUID" /etc/fstab 2>/dev/null || \
      echo "UUID=$UUID $MNT $FSTYPE defaults,nofail 0 0" >>/etc/fstab
  else
    grep -q "$DEV" /etc/fstab 2>/dev/null || \
      echo "$DEV $MNT $FSTYPE defaults,nofail 0 0" >>/etc/fstab
  fi
  mount "$MNT" 2>/dev/null || mount -o "$MNT_OPTS" "$DEV" "$MNT" 2>/dev/null || true
  log "USB: $DEV → $MNT ($FSTYPE)"
else
  log "WARN: USB диск не виден — проверьте порт и переподключите"
fi

# --- 4. Downloads + Samba + Transmission ---
DL="$MNT/downloads"
if [ -d "$MNT" ] && mountpoint -q "$MNT" 2>/dev/null; then
  for cand in "$MNT/download" "$MNT/Download" "$MNT/transmission" "$MNT/downloads"; do
    if [ -d "$cand" ]; then DL="$cand"; break; fi
  done
  mkdir -p "$DL" "$DL/.incomplete"

  T_SETTINGS=""
  for s in "$MNT/transmission/settings.json" "$DL/settings.json" \
    "$MNT/.config/transmission-daemon/settings.json"; do
    [ -f "$s" ] && T_SETTINGS="$s" && break
  done

  uci -q set transmission.transmission=transmission 2>/dev/null || true
  uci set transmission.transmission.enabled='1'
  uci set transmission.transmission.download_dir="$DL"
  uci set transmission.transmission.incomplete_dir="$DL/.incomplete"
  uci set transmission.transmission.incomplete_dir_enabled='1'
  uci set transmission.transmission.config_dir='/etc/transmission/config'
  uci set transmission.transmission.rpc_enabled='1'
  uci set transmission.transmission.rpc_whitelist_enabled='0'
  mkdir -p /etc/transmission/config
  if [ -n "$T_SETTINGS" ]; then
    cp -a "$T_SETTINGS" /etc/transmission/config/settings.json
    sed -i "s|\"download-dir\".*|\"download-dir\": \"$DL\",|" \
      /etc/transmission/config/settings.json 2>/dev/null || true
    log "Transmission: settings.json с диска"
  fi
  uci commit transmission

  uci -q set samba4=samba 2>/dev/null || true
  uci set samba4.@samba[0].name='FLINT'
  uci set samba4.@samba[0].workgroup='WORKGROUP'
  uci set samba4.@samba[0].charset='UTF-8'
  uci -q delete samba4.download 2>/dev/null || true
  uci set samba4.download=sambashare
  uci set samba4.download.name='download'
  uci set samba4.download.path="$DL"
  uci set samba4.download.read_only='no'
  uci set samba4.download.guest_ok='yes'
  uci set samba4.download.create_mask='0664'
  uci set samba4.download.dir_mask='0775'
  uci commit samba4

  curl -fsSL "$BASE/transmission-schedule.sh" -o /etc/transmission-schedule.sh 2>/dev/null || true
  chmod +x /etc/transmission-schedule.sh 2>/dev/null || true
  ( crontab -l 2>/dev/null | grep -v transmission-schedule
    echo "0 1 * * * /etc/transmission-schedule.sh start"
    echo "0 6 * * * /etc/transmission-schedule.sh stop"
    echo "*/10 * * * * /etc/transmission-schedule.sh"
  ) | crontab - 2>/dev/null || true

  /etc/init.d/samba4 enable
  /etc/init.d/samba4 restart
  /etc/init.d/transmission enable
  /etc/init.d/transmission restart 2>/dev/null || /etc/init.d/transmission start 2>/dev/null || true
  log "Samba: \\\\192.168.1.1\\download"
  log "Transmission: $DL"
fi

# --- 5. Amnezia split (awg0 уже через UCI) ---
if [ -f /etc/amnezia/client.env ]; then
  log "Amnezia split..."
  MARK=0x64
  TABLE=100
  IFACE=awg0
  curl -fsSL "$BASE/ai-domains.txt" -o /etc/amnezia/ai-domains.txt 2>/dev/null || true
  mkdir -p /etc/dnsmasq.d /etc/amnezia
  NFTSET_FILE=/etc/dnsmasq.d/ai-vpn.nftset
  : >"$NFTSET_FILE"
  while read -r dom; do
    [ -z "$dom" ] && continue
    case "$dom" in \#*) continue ;; esac
    echo "nftset=/${dom}/4#inet#fw4#ai_vpn" >>"$NFTSET_FILE"
  done </etc/amnezia/ai-domains.txt
  uci set dhcp.@dnsmasq[0].confdir='/etc/dnsmasq.d' 2>/dev/null || true
  uci commit dhcp
  ifup "$IFACE" 2>/dev/null || true
  ip rule del fwmark $MARK table $TABLE 2>/dev/null || true
  ip route flush table $TABLE 2>/dev/null || true
  ip route add default dev "$IFACE" table $TABLE 2>/dev/null || true
  ip rule add fwmark $MARK table $TABLE priority 10050 2>/dev/null || true
  nft list set inet fw4 ai_vpn >/dev/null 2>&1 || \
    nft add set inet fw4 ai_vpn '{ type ipv4_addr; flags interval; }' 2>/dev/null || true
  nft list chain inet fw4 mangle_prerouting >/dev/null 2>&1 || \
    nft add chain inet fw4 mangle_prerouting '{ type filter hook prerouting priority -150; }' 2>/dev/null || true
  nft flush chain inet fw4 mangle_prerouting 2>/dev/null || true
  nft add rule inet fw4 mangle_prerouting ip daddr @ai_vpn meta mark set $MARK 2>/dev/null || true
  iptables -t nat -C POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || true
  cat >/etc/amnezia/start-split.sh <<EOF
#!/bin/sh
IFACE=$IFACE
MARK=$MARK
TABLE=$TABLE
ifup "\$IFACE" 2>/dev/null || true
ip rule add fwmark \$MARK table \$TABLE priority 10050 2>/dev/null || true
ip route add default dev "\$IFACE" table \$TABLE 2>/dev/null || true
EOF
  chmod +x /etc/amnezia/start-split.sh
  /etc/init.d/amnezia-split enable 2>/dev/null || true
  /etc/init.d/dnsmasq restart
fi

# --- 6. Reverse SSH tunnel ---
if [ -x /etc/flint2-tunnel/start.sh ]; then
  /etc/flint2-tunnel/start.sh 2>/dev/null || true
elif curl -fsSL "$BASE/07-router-tunnel.sh" | sh 2>/dev/null; then
  log "туннель VPS создан"
fi

# --- 7. Проверка ---
log "=== итог ==="
/etc/init.d/dnsmasq status 2>&1 | head -1
/etc/init.d/podkop status 2>&1 | head -1
pgrep nfqws >/dev/null && log "zapret: ok" || log "zapret: WARN"
awg show "$IFACE" 2>/dev/null | grep -q handshake && log "amnezia: ok" || log "amnezia: WARN"
mountpoint -q "$MNT" 2>/dev/null && log "usb: mounted" || log "usb: NOT mounted"
curl -4 -sI --max-time 10 https://www.youtube.com/generate_204 2>/dev/null | head -1 || log "youtube: FAIL"
