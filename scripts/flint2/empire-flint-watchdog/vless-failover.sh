#!/bin/sh
# Failover VLESS → zapret. Вызывается из empire-flint-watchdog в режиме vps/auto.
#
# Если TCP на VPS:8443 мёртв и YouTube не открывается — снимаем russia_inside
# (FakeIP больше не перехватывает youtube) и оставляем zapret на WAN.
# Когда VLESS ожил — возвращаем списки. Не трогаем sing-box.json: его пишет podkop.
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

. /etc/empire/mode-lib.sh 2>/dev/null || exit 0

MODE=$(empire_bypass_mode)
empire_is_novps && exit 0
[ "$MODE" = "vps" ] || [ "$MODE" = "auto" ] || exit 0

FAIL_FILE=/tmp/empire-vless-fail.count
OK_FILE=/tmp/empire-vless-ok.count
LIST_BAK=/etc/empire/podkop-lists.bak
STATE=/etc/empire/bypass-state
LOG=/tmp/empire-flint-watchdog.log

log() { echo "$(date -Is 2>/dev/null || date) failover: $*" >>"$LOG"; }

fail_n() { cat "$FAIL_FILE" 2>/dev/null || echo 0; }
ok_n() { cat "$OK_FILE" 2>/dev/null || echo 0; }
bump() { echo $(($1 + 1)) >"$2"; }
resetc() { echo 0 >"$1"; }

youtube_ok() {
  code=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 12 \
    https://www.youtube.com/generate_204 2>/dev/null || echo 000)
  case "$code" in 204|200) return 0 ;; esac
  return 1
}

enter_failover() {
  [ -x /etc/init.d/podkop ] || return 1
  mkdir -p /etc/empire
  uci -q get podkop.main.community_lists >"$LIST_BAK" 2>/dev/null || true
  uci -q delete podkop.main.community_lists
  uci commit podkop
  /etc/init.d/podkop restart 2>/dev/null || true
  sleep 4
  /etc/init.d/zapret restart 2>/dev/null || /etc/init.d/zapret2 restart 2>/dev/null || true
  echo failover >"$STATE"
  log "ENTER failover (VLESS down, YouTube → zapret/WAN)"
}

restore_vps() {
  [ -x /etc/init.d/podkop ] || return 1
  uci -q delete podkop.main.community_lists
  if [ -s "$LIST_BAK" ]; then
    while read -r lst; do
      [ -n "$lst" ] && uci add_list podkop.main.community_lists="$lst"
    done <"$LIST_BAK"
  else
    uci add_list podkop.main.community_lists='russia_inside'
    uci add_list podkop.main.community_lists='telegram'
  fi
  uci commit podkop
  /etc/init.d/podkop restart 2>/dev/null || true
  sleep 6
  echo vps >"$STATE"
  log "RESTORE vps lists"
}

# --- logic ---
vless_up=0
empire_ok_vless_tcp && vless_up=1
yt_up=0
youtube_ok && yt_up=1

st=$(empire_bypass_state)

if [ "$st" != "failover" ]; then
  if [ "$yt_up" = 1 ]; then
    resetc "$FAIL_FILE"
    exit 0
  fi
  if [ "$vless_up" = 0 ]; then
    n=$(fail_n)
    bump "$n" "$FAIL_FILE"
    n=$(fail_n)
    log "VLESS tcp down, youtube fail, count=$n"
    [ "$n" -ge 2 ] && enter_failover
  else
    # VLESS жив, YouTube нет — чинит основной watchdog (podkop/zapret restart)
    resetc "$FAIL_FILE"
  fi
  exit 0
fi

# already failover
if [ "$vless_up" = 1 ]; then
  n=$(ok_n)
  bump "$n" "$OK_FILE"
  n=$(ok_n)
  if [ "$n" -ge 2 ]; then
    restore_vps
    if youtube_ok; then
      resetc "$FAIL_FILE"
      resetc "$OK_FILE"
      log "RESTORE youtube OK"
    else
      log "RESTORE youtube still fail → back to failover"
      enter_failover
      resetc "$OK_FILE"
    fi
  fi
else
  resetc "$OK_FILE"
fi
exit 0
