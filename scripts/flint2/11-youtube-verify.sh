#!/bin/sh
# Проверка YouTube и типичных блокировок. Учитывает режим vps/novps.
set -eu

log() { printf '\033[1;32m[verify]\033[0m %s\n' "$*"; }
fail=0
MODE=vps
[ -f /etc/empire/bypass-mode ] && MODE="$(tr -d '\r\n' </etc/empire/bypass-mode)"
log "режим: $MODE"

check() {
  name="$1"
  url="$2"
  code=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 15 "$url" 2>/dev/null || echo 000)
  case "$code" in
    200|204|301|302) log "OK  $name  http=$code" ;;
    *) log "FAIL $name ($url) http=$code"; fail=1 ;;
  esac
}

log "offload: $(uci -q get firewall.@defaults[0].flow_offloading || echo '?') (должно быть 0)"
log "IPv6 WAN: $(uci -q get network.wan.ipv6 || echo '?') (должно быть 0)"

pgrep -a nfqws 2>/dev/null | head -1 || log "WARN: nfqws не запущен"
if [ "$MODE" != "novps" ]; then
  pgrep -a sing-box 2>/dev/null | head -1 || log "WARN: sing-box не запущен"
  /etc/init.d/podkop status 2>/dev/null || true
fi

log "DNS youtube:"
nslookup www.youtube.com 127.0.0.1 2>/dev/null | awk '/^Address:/{print}' | tail -3 || log "DNS warning"

check "YouTube generate_204" "https://www.youtube.com/generate_204"
check "YouTube" "https://www.youtube.com/"
check "Telegram" "https://telegram.org/"
check "Sber" "https://www.sberbank.ru/"

[ "$fail" -eq 0 ] && log "проверки прошли" || log "есть ошибки — zms / LuCI Podkop Diagnostics / logread"
exit "$fail"
