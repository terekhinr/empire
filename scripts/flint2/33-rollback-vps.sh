#!/bin/sh
# Откат на режим VPS из последнего снимка 32-backup-vps-state.sh
set -eu
BK=""
if [ -n "${1:-}" ] && [ -d "$1" ]; then
  BK="$1"
elif [ -f /etc/empire/rollback-vps/LATEST ]; then
  ST=$(cat /etc/empire/rollback-vps/LATEST)
  BK="/etc/empire/rollback-vps/${ST}"
fi
[ -d "$BK" ] || { echo "[rollback] нет снимка $BK"; exit 1; }

log() { echo "[rollback-vps] $*"; }

log "восстанавливаю из $BK"

[ -f "$BK/bypass-mode" ] && cp -a "$BK/bypass-mode" /etc/empire/bypass-mode
[ -f "$BK/bypass-state" ] && cp -a "$BK/bypass-state" /etc/empire/bypass-state
[ -f "$BK/vps.env" ] && cp -a "$BK/vps.env" /etc/empire/vps.env
echo vps >/etc/empire/bypass-mode
echo vps >/etc/empire/bypass-state

[ -f "$BK/podkop.uci" ] && uci import podkop <"$BK/podkop.uci" && uci commit podkop
[ -f "$BK/dhcp.uci" ] && uci import dhcp <"$BK/dhcp.uci" && uci commit dhcp
[ -f "$BK/firewall.uci" ] && uci import firewall <"$BK/firewall.uci" && uci commit firewall

[ -f "$BK/config.json" ] && cp -a "$BK/config.json" /etc/sing-box/config.json
[ -f "$BK/sing-box.golden.json" ] && cp -a "$BK/sing-box.golden.json" /etc/podkop/sing-box.golden.json

if [ -f "$BK/crontabs.root" ]; then
  cp -a "$BK/crontabs.root" /etc/crontabs/root
  /etc/init.d/cron restart 2>/dev/null || true
fi

/etc/init.d/firewall reload 2>/dev/null || true
/etc/init.d/dnsmasq restart 2>/dev/null || true

/etc/init.d/podkop enable 2>/dev/null || true
/etc/init.d/podkop restart 2>/dev/null || /etc/init.d/podkop start 2>/dev/null || true
sleep 20

[ -x /etc/flint2-tunnel/start.sh ] && /etc/flint2-tunnel/start.sh 2>/dev/null || true
[ -x /etc/empire/enforce-vless-ssh.sh ] && /etc/empire/enforce-vless-ssh.sh 2>/dev/null || true
[ -x /usr/sbin/empire-singbox-mark ] && /usr/sbin/empire-singbox-mark 2>/dev/null || true
[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch 2>/dev/null || true

log "проверка после отката..."
yt=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 15 https://www.youtube.com/generate_204 2>/dev/null || echo 000)
log "youtube=$yt"
ha_tg() { return 0; }
ha_tg "↩️ Flint: откат VPS завершён. YouTube=$yt"
log "готово — режим VPS восстановлен"
