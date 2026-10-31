#!/bin/sh
# Общие функции режима обхода. Ставится в /etc/empire/mode-lib.sh
# shellcheck disable=SC2034

empire_bypass_mode() {
  if [ -f /etc/empire/bypass-mode ]; then
    tr -d '\r\n' </etc/empire/bypass-mode
  else
    echo vps
  fi
}

empire_bypass_state() {
  if [ -f /etc/empire/bypass-state ]; then
    tr -d '\r\n' </etc/empire/bypass-state
  else
    empire_bypass_mode
  fi
}

empire_is_novps() {
  [ "$(empire_bypass_mode)" = "novps" ]
}

empire_in_failover() {
  [ "$(empire_bypass_state)" = "failover" ]
}

empire_vps_host() {
  if [ -f /etc/empire/vps.env ]; then
    # shellcheck disable=SC1091
    . /etc/empire/vps.env
  fi
  echo "${VPS_HOST:-193.233.232.48}"
}

empire_vps_port() {
  if [ -f /etc/empire/vps.env ]; then
    # shellcheck disable=SC1091
    . /etc/empire/vps.env
  fi
  echo "${VPS_PORT:-8443}"
}

empire_ok_offload_off() {
  fo=$(uci -q get firewall.@defaults[0].flow_offloading || echo 0)
  hw=$(uci -q get firewall.@defaults[0].flow_offloading_hw || echo 0)
  [ "$fo" = "0" ] && [ "$hw" = "0" ]
}

empire_fix_offload() {
  uci set firewall.@defaults[0].flow_offloading='0'
  uci set firewall.@defaults[0].flow_offloading_hw='0'
  uci commit firewall
  fw4 reload 2>/dev/null || /etc/init.d/firewall reload 2>/dev/null || true
}

empire_ok_vless_tcp() {
  # Любая из Reality-нод urltest жива → VLESS считается up (не только Empire :8443).
  # Формат строк: host:port
  targets="89.124.76.215:443 132.243.254.241:443 138.124.90.47:8443"
  if [ -f /etc/empire/vless-urltest-targets.txt ]; then
    targets=$(tr '\n' ' ' </etc/empire/vless-urltest-targets.txt)
  fi
  for tp in $targets; do
    host=${tp%%:*}
    port=${tp##*:}
    [ -n "$host" ] && [ -n "$port" ] || continue
    if command -v nc >/dev/null 2>&1; then
      nc -z -w 4 "$host" "$port" >/dev/null 2>&1 && return 0
    elif command -v timeout >/dev/null 2>&1; then
      timeout 4 sh -c "echo >/dev/tcp/$host/$port" 2>/dev/null && return 0
    fi
  done
  # fallback: старый одиночный Empire
  host=$(empire_vps_host)
  port=$(empire_vps_port)
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 5 "$host" "$port" >/dev/null 2>&1 && return 0
  fi
  return 1
}
