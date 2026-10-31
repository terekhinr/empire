#!/bin/sh
# Amnezia awg0: primary (Aeza) и полный профиль backup (Vienna conf).
# Peer-only swap не работает: у Vienna другой PrivateKey и другие Jc/S/H.
# try-backup подставляет весь профиль, ждёт handshake и откатывает
# /etc/config/network, если ответа нет. Иначе дом остаётся на чужих ключах.
set -eu

PRIMARY_HOST="${EMPIRE_AWG_PRIMARY_HOST:-138.124.90.47}"
PRIMARY_PORT="${EMPIRE_AWG_PRIMARY_PORT:-39182}"
VIENNA_CONF="${EMPIRE_AWG_VIENNA_CONF:-/etc/amnezia/awg0-vienna.conf}"
STATE_DIR=/etc/empire
STATE_FILE=$STATE_DIR/awg-active
PRIMARY_NET=$STATE_DIR/network.awg-primary
LOG=/tmp/empire-awg-failover.log
STALE_SEC="${EMPIRE_AWG_STALE_SEC:-180}"
HOLD_SEC="${EMPIRE_AWG_HOLD_SEC:-21600}"
LOCK=/var/lock/empire-heal.lock
TRY_TS=/tmp/empire-awg-try.ts

log() { echo "$(date -Is 2>/dev/null || date) awg-failover: $*" >>"$LOG"; }

active() { cat "$STATE_FILE" 2>/dev/null || echo primary; }

handshake_age() {
  line=$(awg show awg0 2>/dev/null | grep 'latest handshake' || true)
  [ -n "$line" ] || { echo 999999; return; }
  echo "$line" | grep -qi 'never\|handshake did not' && { echo 999999; return; }
  sec=0
  echo "$line" | grep -qoE '[0-9]+ day' && d=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) day.*/\1/p') && sec=$((sec + d * 86400))
  echo "$line" | grep -qoE '[0-9]+ hour' && h=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) hour.*/\1/p') && sec=$((sec + h * 3600))
  echo "$line" | grep -qoE '[0-9]+ minute' && m=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) minute.*/\1/p') && sec=$((sec + m * 60))
  echo "$line" | grep -qoE '[0-9]+ second' && s=$(echo "$line" | sed -n 's/.*\([0-9][0-9]*\) second.*/\1/p') && sec=$((sec + s))
  echo "$sec"
}

# Первое поле до знака =. Хвост base64 с '=' не съедается (старый sed .*= ломал ключ).
conf_field() {
  awk -v k="$1" '
    $0 ~ "^" k "[[:space:]]*=" {
      sub(/^[^=]*=[[:space:]]*/, "")
      gsub(/\r/, "")
      print
      exit
    }
  ' "$VIENNA_CONF"
}

save_primary_net() {
  mkdir -p "$STATE_DIR"
  if [ -f "$PRIMARY_NET" ]; then
    return 0
  fi
  cur=$(uci -q get network.@amneziawg_awg0[0].endpoint_host || true)
  if [ "$cur" != "$PRIMARY_HOST" ]; then
    log "refuse snapshot: endpoint is $cur, not $PRIMARY_HOST"
    return 1
  fi
  cp -a /etc/config/network "$PRIMARY_NET"
  chmod 600 "$PRIMARY_NET"
  log "saved primary network snapshot"
}

apply_vienna() {
  priv=$(conf_field PrivateKey)
  pub=$(conf_field PublicKey)
  psk=$(conf_field PresharedKey)
  ep=$(conf_field Endpoint)
  jc=$(conf_field Jc)
  jmin=$(conf_field Jmin)
  jmax=$(conf_field Jmax)
  s1=$(conf_field S1)
  s2=$(conf_field S2)
  s3=$(conf_field S3)
  s4=$(conf_field S4)
  h1=$(conf_field H1)
  h2=$(conf_field H2)
  h3=$(conf_field H3)
  h4=$(conf_field H4)
  host=${ep%:*}
  port=${ep##*:}
  [ -n "$priv" ] && [ -n "$pub" ] && [ -n "$host" ] && [ -n "$port" ] || return 1
  uci set network.awg0.private_key="$priv"
  [ -n "$jc" ] && uci set network.awg0.awg_jc="$jc"
  [ -n "$jmin" ] && uci set network.awg0.awg_jmin="$jmin"
  [ -n "$jmax" ] && uci set network.awg0.awg_jmax="$jmax"
  [ -n "$s1" ] && uci set network.awg0.awg_s1="$s1"
  [ -n "$s2" ] && uci set network.awg0.awg_s2="$s2"
  [ -n "$s3" ] && uci set network.awg0.awg_s3="$s3"
  [ -n "$s4" ] && uci set network.awg0.awg_s4="$s4"
  [ -n "$h1" ] && uci set network.awg0.awg_h1="$h1"
  [ -n "$h2" ] && uci set network.awg0.awg_h2="$h2"
  [ -n "$h3" ] && uci set network.awg0.awg_h3="$h3"
  [ -n "$h4" ] && uci set network.awg0.awg_h4="$h4"
  uci set network.@amneziawg_awg0[0].public_key="$pub"
  [ -n "$psk" ] && uci set network.@amneziawg_awg0[0].preshared_key="$psk"
  uci set network.@amneziawg_awg0[0].endpoint_host="$host"
  uci set network.@amneziawg_awg0[0].endpoint_port="$port"
  uci commit network
  log "applied vienna profile $host:$port"
}

rollback_primary() {
  if [ ! -f "$PRIMARY_NET" ]; then
    log "rollback missing $PRIMARY_NET"
    return 1
  fi
  cp -a "$PRIMARY_NET" /etc/config/network
  ifdown awg0 2>/dev/null || true
  sleep 1
  ifup awg0 2>/dev/null || true
  echo primary >"$STATE_FILE"
  log "rolled back to primary snapshot"
}

try_backup() {
  mkdir -p "$STATE_DIR"
  [ -f "$VIENNA_CONF" ] || { log "no vienna conf file"; return 1; }
  save_primary_net || return 1
  date +%s >"$TRY_TS"
  log "try vienna full profile"
  if ! apply_vienna; then
    log "vienna profile incomplete, rollback"
    rollback_primary || true
    return 1
  fi
  ifdown awg0 2>/dev/null || true
  sleep 1
  ifup awg0 2>/dev/null || true
  sleep 18
  age=$(handshake_age)
  if [ "$age" -lt "$STALE_SEC" ]; then
    echo vienna >"$STATE_FILE"
    log "vienna OK age=${age}s"
    return 0
  fi
  log "vienna no handshake age=${age}s, rollback"
  rollback_primary || true
  return 1
}

ensure() {
  mkdir -p "$STATE_DIR"
  age=$(handshake_age)
  log "check active=$(active) handshake_age=${age}s endpoint=$(uci -q get network.@amneziawg_awg0[0].endpoint_host || true)"
  if [ "$age" -lt "$STALE_SEC" ]; then
    return 0
  fi
  # Сам не переключаем endpoint: ifup не пробивает пропавший UDP,
  # а чужой профиль без ответа только роняет интерфейс. Проба — вручную: try-backup.
  now=$(date +%s)
  last=0
  [ -f "$TRY_TS" ] && last=$(cat "$TRY_TS" 2>/dev/null || echo 0)
  if [ $((now - last)) -ge "$HOLD_SEC" ]; then
    date +%s >"$TRY_TS"
    log "stale age=${age}s. UDP уходит в WAN и не возвращается. ifup не поможет. Ручная проба: try-backup"
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
  try-backup)
    flock -n "$LOCK" env EMPIRE_HEAL_LOCKED=1 "$0" try-backup-locked
    ;;
  try-backup-locked)
    try_backup
    ;;
  *)
    echo "usage: $0 ensure|status|try-backup" >&2
    exit 2
    ;;
esac
