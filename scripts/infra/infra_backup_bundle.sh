#!/usr/bin/env bash
# Сбор infra-пакета перед выгрузкой на Я.Диск
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
INFRA="${ROOT}/data/infra"
STAMP="$(date +%Y-%m-%dT%H%M%S)"

log() { echo "[$(date -Iseconds)] $*"; }

mkdir -p "${INFRA}/nginx" "${INFRA}/systemd" "${INFRA}/home-router"

log "=== infra backup bundle ==="

# Документация (копия для offline на Диске)
if [[ -d "${ROOT}/docs/infra" ]]; then
  rsync -a --delete "${ROOT}/docs/infra/" "${INFRA}/docs/" 2>/dev/null || cp -a "${ROOT}/docs/infra" "${INFRA}/docs"
  log "docs/infra → data/infra/docs"
fi

# Nginx из репо (prod конфиг)
[[ -d "${ROOT}/deploy/nginx" ]] && rsync -a "${ROOT}/deploy/nginx/" "${INFRA}/nginx/" && log "deploy/nginx"

# systemd: units + timers из repo и /etc
for pattern in empire obsidian empire-night empire-vps empire-ha; do
  for u in "${ROOT}/deploy/"*.service "${ROOT}/deploy/"*.timer; do
    [[ -f "$u" ]] && cp -a "$u" "${INFRA}/systemd/" 2>/dev/null || true
  done
done
for u in /etc/systemd/system/empire*.service /etc/systemd/system/empire*.timer \
         /etc/systemd/system/obsidian*.service /etc/systemd/system/obsidian*.timer; do
  [[ -f "$u" ]] && cp -a "$u" "${INFRA}/systemd/" || true
done
log "systemd units"

# rclone.conf (критично для restore — секрет!)
if [[ -f /root/.config/rclone/rclone.conf ]]; then
  install -m 600 /root/.config/rclone/rclone.conf "${INFRA}/rclone.conf.backup"
  log "rclone.conf.backup (600)"
fi

# crontab
crontab -l > "${INFRA}/crontab-root.txt" 2>/dev/null || true

# flint2 scripts manifest
ls -la "${ROOT}/scripts/flint2/" > "${INFRA}/flint2-manifest.txt" 2>/dev/null || true

# Домашний роутер
if [[ -x "${ROOT}/scripts/infra/home_router_backup.sh" ]]; then
  EMPIRE_ROOT="$ROOT" "${ROOT}/scripts/infra/home_router_backup.sh" || log "WARN: home_router_backup failed"
fi

# Манифест
cat > "${INFRA}/MANIFEST.txt" <<EOF
infra bundle ${STAMP}
host=$(hostname -s)
empire_root=${ROOT}
docs=docs/infra/
restore_vps=scripts/infra/vps_restore_from_yandex.sh
restore_home=docs/infra/HOME_NETWORK.md
EOF

log "DONE → ${INFRA}/"
