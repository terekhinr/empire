#!/bin/bash
# TOX1: починить Supervisor + восстановить бэкап из /usr/share/hassio/backup/
# Запуск на боксе: bash tox1_ha_restore_all.sh
set -euo pipefail

BACKUP_DIR=/usr/share/hassio/backup
BACKUP_GLOB='Full Backup 2026-06-08*.tar'

log() { echo "[tox1] $*"; }

log "=== 1/5 Дополнения: docker_gateway_unprotected ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y iptables nftables dbus >/dev/null
if [[ -f /etc/docker/daemon.json ]] && grep -qE '"iptables"\s*:\s*false' /etc/docker/daemon.json 2>/dev/null; then
  python3 -c "import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text());d.pop('iptables',None);d.pop('ip6tables',None);p.write_text(json.dumps(d,indent=2)+'\n')"
  log "Убрали iptables:false из docker"
fi
systemctl enable --now dbus
systemctl restart docker
sleep 3
ha jobs options --ignore-conditions healthy
ha supervisor reload
sleep 12

log "=== 2/5 Файлы бэкапа ==="
ls -lah "$BACKUP_DIR"/ || true

log "=== 3/5 Пересканировать бэкапы ==="
ha supervisor restart
sleep 20

log "=== 4/5 Список (ha backups list) ==="
ha backups list || true

SLUG=""
if ha backups list --raw-json >/tmp/ha_backups.json 2>/dev/null; then
  SLUG=$(python3 - <<'PY'
import json, pathlib
raw = pathlib.Path("/tmp/ha_backups.json").read_text()
data = json.loads(raw)
backups = data.get("data", {}).get("backups") or data.get("backups") or []
want = "Full Backup 2026-06-08"
for b in backups:
    if want in (b.get("name") or ""):
        print(b.get("slug", ""))
        break
else:
    if backups:
        print(backups[-1].get("slug", ""))
PY
)
fi

if [[ -z "$SLUG" ]]; then
  # slug: в YAML-выводе ha backups list (не путать с id дополнений 5c53de3b_*)
  SLUG=$(ha backups list 2>/dev/null | awk '/^slug:/{print $2; exit}' || true)
fi
if [[ -z "$SLUG" ]]; then
  SLUG=$(ha backups list 2>/dev/null | grep -oE '^[[:space:]]*-[[:space:]]*slug:[[:space:]]*[0-9a-f]{8}' | head -1 | grep -oE '[0-9a-f]{8}$' || true)
fi

if [[ -z "$SLUG" ]]; then
  TAR=$(ls -1 "$BACKUP_DIR"/$BACKUP_GLOB 2>/dev/null | head -1 || ls -1 "$BACKUP_DIR"/*.tar 2>/dev/null | head -1 || true)
  if [[ -n "$TAR" && -f "$TAR" ]]; then
    log "Slug не найден — копируем ещё раз и перезапускаем supervisor"
    cp -f "$TAR" "$BACKUP_DIR/$(basename "$TAR")"
    ha supervisor restart
    sleep 25
    ha backups list || true
    SLUG=$(ha backups list 2>/dev/null | awk '/^slug:/{print $2; exit}' || true)
  fi
fi

if [[ -z "$SLUG" ]]; then
  log "ОШИБКА: slug не найден. Пришлите вывод: ha backups list"
  exit 1
fi

log "=== 5/5 Ждём готовности Supervisor ==="
for i in $(seq 1 36); do
  STATE=$(ha supervisor info 2>/dev/null | awk '/^state:/{print $2}' || true)
  if [[ "$STATE" == "running" ]]; then
    log "Supervisor: running"
    break
  fi
  log "Supervisor: ${STATE:-unknown}, ждём... ($i/36)"
  sleep 10
done

log "=== Восстановление slug=$SLUG (5–15 мин) ==="
ha backups restore "$SLUG"

log "Готово. HA перезагрузится сам. Открой http://192.168.1.41:8123 через 5–10 мин"
