#!/bin/sh
# Amnezia awg0: primary (Aeza) ↔ backup (Vienna conf).
# Паттерн как urltest, но для одного system-интерфейса AmneziaWG:
# stale handshake → полный swap peer из /etc/amnezia/awg0-vienna.conf → ifup.
# Возврат на primary после N успешных handshake на backup (раз в цикл).
set -eu

PRIMARY_HOST="${EMPIRE_AWG_PRIMARY_HOST:-138.124.90.47}"
PRIMARY_PORT="${EMPIRE_AWG_PRIMARY_PORT:-39182}"
VIENNA_CONF="${EMPIRE_AWG_VIENNA_CONF:-/etc/amnezia/awg0-vienna.conf}"
STATE_DIR=/etc/empire
STATE_FILE=$STATE_DIR/awg-active
LOG=/tmp/empire-awg-failover.log
STALE_SEC="${EMPIRE_AWG_STALE_SEC:-180}"
LOCK=/var/lock/empire-heal.lock

log() { echo "$(date -Is 2>/dev/null || date) awg-failover: $*" >>"$LOG"; }

active() { cat "$STATE_FILE" 2>/dev/null || echo primary; }

handshake_age() {
  # "latest handshake: 1 minute, 30 seconds ago" / "2 hours, 3 minutes ago" / never
  line=$(awg show awg0 2>/dev/null | grep 'latest handshake' || true)
  [ -n "$line" ] || { echo 999999; return; }
  echo "$line" | grep -qi 'never\|handshake did not' && { echo 999999; return; }
  # parse rough seconds
  sec=0
  echo "$line" | grep -qoE '[0-9]+ day' && d=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) day.*/\1/p') && sec=$((sec + d * 86400))
  echo "$line" | grep -qoE '[0-9]+ hour' && h=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) hour.*/\1/p') && sec=$((sec + h * 3600))
  echo "$line" | grep -qoE '[0-9]+ minute' && m=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) minute.*/\1/p') && sec=$((sec + m * 60))
  echo "$line" | grep -qoE '[0-9]+ second' && s=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) second.*/\1/p') && sec=$((sec + s))
  # "just now" / empty numbers
  [ "$sec" -eq 0 ] && echo "$line" | grep -qi 'ago' || true
  echo "$sec"
}

uci_set_peer() {
  host="$1"; port="$2"; pub="$3"; psk="$4"
  # first amneziawg_awg0 section
  sid=$(uci show network | sed -n "s/^network\.\\(@amneziawg_awg0\\[[0-9]\\]\\)=amneziawg_awg0/\\1/p" | head -1)
  [ -n "$sid" ] || return 1
  uci set "network.$sid.endpoint_host=$host"
  uci set "network.$sid.endpoint_port=$port"
  uci set "network.$sid.public_key=$pub"
  [ -n "$psk" ] && uci set "network.$sid.preshared_key=$psk"
  uci commit network
  ifdown awg0 2>/dev/null || true
  sleep 1
  ifup awg0 2>/dev/null || true
  sleep 3
}

parse_vienna() {
  # sets VIENNA_HOST PORT PUB PSK PRIV ADDR
  VIENNA_HOST=""; VIENNA_PORT=""; VIENNA_PUB=""; VIENNA_PSK=""
  [ -f "$VIENNA_CONF" ] || return 1
  ep=$(grep -E '^Endpoint[[:space:]]*=' "$VIENNA_CONF" | head -1 | sed 's/.*=[[:space:]]*//;s/[[:space:]]*$//')
  VIENNA_HOST=${ep%:*}; VIENNA_PORT=${ep##*:}
  VIENNA_PUB=$(grep -E '^PublicKey[[:space:]]*=' "$VIENNA_CONF" | head -1 | sed 's/.*=[[:space:]]*//;s/[[:space:]]*$//')
  VIENNA_PSK=$(grep -E '^PresharedKey[[:space:]]*=' "$VIENNA_CONF" | head -1 | sed 's/.*=[[:space:]]*//;s/[[:space:]]*$//')
  [ -n "$VIENNA_HOST" ] && [ -n "$VIENNA_PUB" ] || return 1
  return 0
}

primary_pub() {
  # текущий primary pubkey храним при первом switch, иначе из client.env bak
  if [ -f "$STATE_DIR/awg-primary.peer" ]; then
    cat "$STATE_DIR/awg-primary.peer"
    return
  fi
  pub=$(uci -q get network.@amneziawg_awg0[0].public_key || true)
  psk=$(uci -q get network.@amneziawg_awg0[0].preshared_key || true)
  echo "$PRIMARY_HOST|$PRIMARY_PORT|$pub|$psk" >"$STATE_DIR/awg-primary.peer"
  cat "$STATE_DIR/awg-primary.peer"
}

switch_to_vienna() {
  parse_vienna || { log "no vienna conf"; return 1; }
  primary_pub >/dev/null
  log "switch → vienna $VIENNA_HOST:$VIENNA_PORT"
  uci_set_peer "$VIENNA_HOST" "$VIENNA_PORT" "$VIENNA_PUB" "$VIENNA_PSK" || return 1
  echo vienna >"$STATE_FILE"
  age=$(handshake_age)
  [ "$age" -lt "$STALE_SEC" ] && log "vienna OK age=${age}s" && return 0
  log "vienna still stale age=${age}s"
  return 1
}

switch_to_primary() {
  [ -f "$STATE_DIR/awg-primary.peer" ] || return 1
  IFS='|' read -r h p pub psk <"$STATE_DIR/awg-primary.peer"
  log "switch → primary $h:$p"
  uci_set_peer "$h" "$p" "$pub" "$psk" || return 1
  echo primary >"$STATE_FILE"
  age=$(handshake_age)
  [ "$age" -lt "$STALE_SEC" ] && log "primary OK age=${age}s" && return 0
  log "primary still stale age=${age}s"
  return 1
}

ensure() {
  mkdir -p "$STATE_DIR"
  # save primary once while healthy on primary
  if [ "$(active)" = "primary" ] || [ ! -f "$STATE_DIR/awg-primary.peer" ]; then
    cur=$(uci -q get network.@amneziawg_awg0[0].endpoint_host || true)
    if [ "$cur" = "$PRIMARY_HOST" ]; then
      primary_pub >/dev/null
    fi
  fi

  age=$(handshake_age)
  cur=$(active)
  log "check active=$cur handshake_age=${age}s"

  if [ "$age" -lt "$STALE_SEC" ]; then
    # healthy: if on vienna, optionally try primary back every ~30 min marker
    if [ "$cur" = "vienna" ]; then
      now=$(date +%s)
      last=0
      [ -f /tmp/empire-awg-primary-try.ts ] && last=$(cat /tmp/empire-awg-primary-try.ts)
      if [ $((now - last)) -ge 1800 ]; then
        echo "$now" >/tmp/empire-awg-primary-try.ts
        switch_to_primary || switch_to_vienna || true
      fi
    fi
    return 0
  fi

  # stale
  if [ "$cur" = "primary" ]; then
    switch_to_vienna || true
  else
    switch_to_primary || switch_to_vienna || true
  fi
}

cmd="${1:-ensure}"
case "$cmd" in
  status)
    echo "active=$(active) age=$(handshake_age)"
    awg show awg0 2>/dev/null | grep -E 'endpoint|handshake|transfer' || true
    ;;
  ensure)
    if [ -n "${EMPIRE_HEAL_LOCKED:-}" ]; then
      ensure
    else
      flock -n "$LOCK" env EMPIRE_HEAL_LOCKED=1 "$0" ensure || ensure
    fi
    ;;
  *)
    echo "usage: $0 ensure|status" >&2
    exit 2
    ;;
esac
