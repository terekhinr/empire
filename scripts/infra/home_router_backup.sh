#!/usr/bin/env bash
# Снимок конфигурации Flint/Keenetic → data/infra/home-router/
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
OUT="${ROOT}/data/infra/home-router"
STAMP="$(date +%Y-%m-%dT%H%M%S)"
HA_TS="${HA_SSH:-root@100.80.133.85}"
FLINT="192.168.1.1"

log() { echo "[$(date -Iseconds)] $*"; }

mkdir -p "$OUT"

# Статические экспорты из репо (всегда)
for f in keenetic-export.json keenetic-snapshot.json dhcp-static-leases.sh; do
  src="${ROOT}/scripts/flint2/${f}"
  [[ -f "$src" ]] && cp -a "$src" "${OUT}/${f}" && log "copied ${f}"
done

# Живой Flint через Home Assistant (жёсткий timeout — не блокировать night-pipeline)
SSH_BASE=(ssh -o BatchMode=yes -o ConnectTimeout=6 -o ServerAliveInterval=3 -o ServerAliveCountMax=2 -o StrictHostKeyChecking=accept-new)
ha_flint() {
  timeout 45 "${SSH_BASE[@]}" "$HA_TS" "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new root@${FLINT} $1"
}

if ha_flint "'echo OK'" 2>/dev/null | grep -q OK; then
  log "Flint reachable via HA — exporting UCI"
  ha_flint "'uci export'" > "${OUT}/flint-uci-${STAMP}.conf" 2>/dev/null || true
  ha_flint "'tar czf - /etc/config 2>/dev/null'" > "${OUT}/flint-etc-config-${STAMP}.tar.gz" 2>/dev/null || true
  ha_flint "'
    echo HOSTNAME=\$(uci get system.@system[0].hostname 2>/dev/null)
    /etc/init.d/dnsmasq status 2>&1 | head -1
    /etc/init.d/podkop status 2>&1 | head -1
    /etc/init.d/samba4 status 2>&1 | head -1
    mount | grep /mnt/usb || true
    awg show awg0 2>/dev/null | grep handshake || true
  '" > "${OUT}/flint-status-${STAMP}.txt" 2>/dev/null || true
  ln -sf "flint-uci-${STAMP}.conf" "${OUT}/flint-uci-latest.conf"
  log "Flint export OK"
else
  log "WARN: Flint not reachable via ${HA_TS} — static keenetic export only"
fi

# README в каталоге
cat > "${OUT}/README.txt" <<EOF
Домашний роутер — бэкап ${STAMP}
Восстановление: docs/infra/HOME_NETWORK.md
flint-uci-latest.conf → ssh root@192.168.1.1 "uci import < ..."
EOF

log "DONE → ${OUT}"
