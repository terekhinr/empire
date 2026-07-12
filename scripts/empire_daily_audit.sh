#!/usr/bin/env bash
# Ежедневный аудит VPS + HA: уязвимости, бэкапы, диск, целостность кода, сервисы.
# Лог: /var/log/empire/daily-audit-*.log · Telegram: краткий отчёт (всегда; ⚠ при проблемах).
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="${LOG_DIR}/daily-audit-${STAMP}.log"
LATEST_LINK="${LOG_DIR}/daily-audit-latest.log"
LOCK="/var/lock/empire-daily-audit.lock"

REMOTE="${RCLONE_REMOTE:-yandex}"
HOST="$(hostname -s 2>/dev/null || echo vps)"
REMOTE_BASE="${RCLONE_BACKUP_REMOTE_PATH:-VPS-backup}/${HOST}"
LOCAL_DB_DIR="${EMPIRE_BACKUP_DIR:-/var/backups/empire}"
HA_SSH="${EMPIRE_HA_SSH:-root@100.80.133.85}"
DISK_WARN="${EMPIRE_AUDIT_DISK_WARN_PCT:-85}"
DISK_CRIT="${EMPIRE_AUDIT_DISK_CRIT_PCT:-92}"
HA_BACKUP_MIN="${EMPIRE_AUDIT_HA_BACKUP_MIN:-1}"
HA_BACKUP_MAX_AGE_DAYS="${EMPIRE_AUDIT_HA_BACKUP_MAX_AGE_DAYS:-8}"
YANDEX_BACKUP_MAX_AGE_DAYS="${EMPIRE_AUDIT_YANDEX_BACKUP_MAX_AGE_DAYS:-2}"
TELEGRAM_MAX="${EMPIRE_AUDIT_TELEGRAM_MAX:-3500}"

mkdir -p "$LOG_DIR"
exec >>"$REPORT" 2>&1
ln -sf "$REPORT" "$LATEST_LINK"

ISSUES=0
WARNINGS=0
TELEGRAM_LINES=()

log() { echo "[$(date -Iseconds)] $*"; }

add_issue() {
  ISSUES=$((ISSUES + 1))
  log "ISSUE: $*"
  TELEGRAM_LINES+=("❌ $*")
}

add_warn() {
  WARNINGS=$((WARNINGS + 1))
  log "WARN: $*"
  TELEGRAM_LINES+=("⚠️ $*")
}

add_ok() {
  log "OK: $*"
}

section() {
  log ""
  log "=== $* ==="
}

exec 9>"$LOCK"
if ! flock -n 9; then
  log "SKIP: другой daily-audit уже идёт"
  exit 0
fi

log "=== empire daily audit start (host=$HOST) ==="

section "Диск"
while read -r fs size used avail pct mount; do
  [[ "$fs" == "Filesystem" ]] && continue
  pct_num="${pct%%%}"
  line="$mount: $used / $size ($pct), свободно $avail"
  if [[ "$pct_num" -ge "$DISK_CRIT" ]]; then
    add_issue "Диск $line"
  elif [[ "$pct_num" -ge "$DISK_WARN" ]]; then
    add_warn "Диск $line"
  else
    add_ok "$line"
  fi
done < <(df -hP / "$LOCAL_DB_DIR" 2>/dev/null | tail -n +1)

section "Крупные каталоги empire (top-5)"
du -xhd1 "$ROOT" 2>/dev/null | sort -hr | head -6 | while read -r sz path; do
  log "  $sz  $path"
done || true

section "Целостность кода (guard)"
if [[ -x "$ROOT/scripts/guard_critical_files.sh" ]]; then
  if "$ROOT/scripts/guard_critical_files.sh" --warn; then
    add_ok "guard_critical_files прошёл"
  else
    add_issue "guard_critical_files не прошёл"
  fi
else
  add_warn "нет scripts/guard_critical_files.sh"
fi

section "Git на VPS"
if [[ -d "$ROOT/.git" ]]; then
  git -C "$ROOT" log -1 --format='последний коммит: %h %ci %s' 2>/dev/null || add_warn "git log недоступен"
  dirty="$(git -C "$ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$dirty" -gt 0 ]]; then
    add_warn "git: $dirty незакоммиченных изменений на VPS"
  else
    add_ok "git: рабочая копия чистая"
  fi
else
  add_warn "нет .git на VPS — локальная история не ведётся"
fi

section "Локальные SQLite-бэкапы ($LOCAL_DB_DIR)"
db_count="$(find "$LOCAL_DB_DIR" -maxdepth 1 -name '*.db' 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$db_count" -eq 0 ]]; then
  add_issue "локальных .db бэкапов: 0 (ожидался backup_empire_db.sh / cron 03:15)"
else
  latest_db="$(find "$LOCAL_DB_DIR" -maxdepth 1 -name '*.db' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
  latest_db_age="$(( ($(date +%s) - $(stat -c %Y "$latest_db" 2>/dev/null || echo 0)) / 86400 ))"
  add_ok "локальных .db: $db_count, последний: $(basename "$latest_db") (${latest_db_age}d назад)"
  if [[ "$latest_db_age" -gt 2 ]]; then
    add_warn "локальный SQLite-бэкап старше 2 дней"
  fi
fi

section "Yandex VPS-бэкапы (${REMOTE}:${REMOTE_BASE})"
if rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
  mapfile -t yandex_days < <(rclone lsf "${REMOTE}:${REMOTE_BASE}/" --dirs-only 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}/$' | sed 's#/##' | sort || true)
  yandex_n="${#yandex_days[@]}"
  if [[ "$yandex_n" -eq 0 ]]; then
    add_issue "на Я.Диске нет дневных папок VPS-backup"
  else
    latest_day="${yandex_days[${#yandex_days[@]}-1]}"
    add_ok "дневных копий на Я.Диске: $yandex_n (последняя: $latest_day)"
    today="$(date +%Y-%m-%d)"
    if [[ "$latest_day" != "$today" ]]; then
      age_days="$(( ($(date +%s) - $(date -d "$latest_day" +%s 2>/dev/null || echo 0)) / 86400 ))"
      if [[ "$age_days" -gt "$YANDEX_BACKUP_MAX_AGE_DAYS" ]]; then
        add_issue "последний Yandex-бэкап $latest_day (старше ${YANDEX_BACKUP_MAX_AGE_DAYS}d)"
      elif pgrep -f 'empire_night_pipeline|vps_backup_to_yandex|tox1-yandex|rclone copyto.*TOX1' >/dev/null 2>&1; then
        add_ok "Yandex-бэкап в процессе (пайплайн/TOX1)"
      else
        add_warn "сегодняшний Yandex-бэкап ещё не завершён (latest=$latest_day)"
      fi
    fi
    # Проверка целостности main.py (latest или последняя дневная папка)
    main_size=0
    for cloud_day in latest "$latest_day"; do
      sz="$(rclone cat "${REMOTE}:${REMOTE_BASE}/${cloud_day}/empire/main.py" 2>/dev/null | wc -c | awk '{print $1}')"
      sz="${sz:-0}"
      if [[ "$sz" -ge 100000 ]]; then
        main_size="$sz"
        add_ok "Yandex ${cloud_day}/main.py OK ($main_size байт)"
        break
      fi
    done
    if [[ "$main_size" -lt 100000 ]]; then
      add_issue "Yandex main.py подозрителен или отсутствует (latest и $latest_day)"
    fi
    sqlite_cloud="$(rclone lsf "${REMOTE}:${REMOTE_BASE}/${latest_day}/sqlite-backups/" 2>/dev/null | grep -c '\.db$' || true)"
    if [[ "$sqlite_cloud" -eq 0 ]]; then
      add_warn "в $latest_day нет sqlite-backups/*.db на Я.Диске"
    else
      add_ok "sqlite-backups в $latest_day: $sqlite_cloud файл(ов)"
    fi
  fi
else
  add_issue "rclone remote ${REMOTE} не настроен"
fi

section "Статус empire-vps-backup-yandex"
if systemctl is-active --quiet empire-vps-backup-yandex.service 2>/dev/null; then
  add_warn "бэкап на Я.Диск СЕЙЧАС выполняется (долго — норма для больших PDF)"
elif systemctl is-failed --quiet empire-vps-backup-yandex.service 2>/dev/null; then
  add_issue "последний empire-vps-backup-yandex завершился с ошибкой"
  journalctl -u empire-vps-backup-yandex.service -n 5 --no-pager 2>/dev/null | while read -r jl; do log "  $jl"; done || true
else
  last_backup_line="$(journalctl -u empire-vps-backup-yandex.service --since '36 hours ago' --no-pager 2>/dev/null | grep -E 'DONE|ERROR|Failed|guard' | tail -1 || true)"
  if [[ -z "$last_backup_line" ]]; then
    add_warn "нет записей empire-vps-backup-yandex за 36ч"
  elif echo "$last_backup_line" | grep -qE 'DONE|Stopped empire-vps-backup'; then
    if echo "$last_backup_line" | grep -q 'Failed'; then
      add_issue "бэкап: $last_backup_line"
    else
      add_ok "последний бэкап: $(echo "$last_backup_line" | sed 's/.*] //')"
    fi
  else
    add_warn "бэкап: $last_backup_line"
  fi
fi

section "Home Assistant ($HA_SSH)"
ha_json="$(ssh -o ConnectTimeout=8 -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HA_SSH" \
  'ha backups list --raw-json 2>/dev/null' 2>/dev/null || true)"
if [[ -z "$ha_json" ]]; then
  add_issue "HA недоступен по SSH ($HA_SSH)"
else
  ha_info="$(python3 - "$ha_json" "$HA_BACKUP_MIN" "$HA_BACKUP_MAX_AGE_DAYS" <<'PY'
import json, sys
from datetime import datetime, timezone

raw, min_b, max_age = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
data = json.loads(raw)
backups = data.get("data", {}).get("backups") or data.get("backups") or []
if not backups:
    print("ISSUE|HA локальных бэкапов: 0")
    sys.exit(0)
latest = max(backups, key=lambda b: b.get("date") or "")
name = latest.get("name", "?")
slug = latest.get("slug", "?")
size = latest.get("size", "?")
date_s = latest.get("date", "")
try:
    dt = datetime.fromisoformat(date_s.replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
except Exception:
    age = 999
print(f"OK|HA бэкапов: {len(backups)}, последний: {name} ({size} MB, slug={slug}, {age}d назад)")
if len(backups) < min_b:
    print(f"ISSUE|HA бэкапов меньше минимума ({len(backups)} < {min_b})")
if age > max_age:
    print(f"ISSUE|HA последний бэкап старше {max_age}d ({age}d)")
PY
)"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    kind="${line%%|*}"
    msg="${line#*|}"
    case "$kind" in
      ISSUE) add_issue "$msg" ;;
      WARN) add_warn "$msg" ;;
      *) add_ok "$msg" ;;
    esac
  done <<< "$ha_info"

  ha_df="$(ssh -o ConnectTimeout=8 -o BatchMode=yes "$HA_SSH" 'df -hP / | tail -1' 2>/dev/null || true)"
  if [[ -n "$ha_df" ]]; then
    ha_pct="$(echo "$ha_df" | awk '{print $5}' | tr -d '%')"
    log "  HA disk: $ha_df"
    if [[ "$ha_pct" -ge "$DISK_CRIT" ]]; then
      add_issue "HA диск заполнен на ${ha_pct}%"
    elif [[ "$ha_pct" -ge "$DISK_WARN" ]]; then
      add_warn "HA диск ${ha_pct}%"
    fi
  fi
fi

section "Уязвимости Python (pip-audit)"
PIP_AUDIT="$ROOT/venv/bin/pip-audit"
if [[ ! -x "$PIP_AUDIT" ]]; then
  add_warn "pip-audit не установлен — запустите: $ROOT/venv/bin/pip install pip-audit"
else
  audit_out="$(mktemp)"
  set +e
  "$PIP_AUDIT" --progress-spinner off --desc on 2>&1 | tee "$audit_out"
  audit_rc="${PIPESTATUS[0]}"
  vuln_pkgs="$(grep -oE 'Found [0-9]+ known vulnerabilit' "$audit_out" | grep -oE '[0-9]+' | head -1 || true)"
  vuln_pkgs="${vuln_pkgs:-0}"
  rm -f "$audit_out"
  if [[ "$vuln_pkgs" -gt 0 ]]; then
    add_issue "pip-audit: уязвимости в $vuln_pkgs пакет(ах) (torch CVE без фикса — локальный JIT) — см. $REPORT"
  elif [[ "$audit_rc" -ne 0 ]]; then
    add_warn "pip-audit завершился с кодом $audit_rc"
  else
    add_ok "pip-audit: уязвимостей не найдено"
  fi
fi

section "APT security updates"
if command -v apt-get >/dev/null 2>&1; then
  apt_out="$(apt-get -s upgrade 2>/dev/null | grep -ci security 2>/dev/null | head -1 | tr -d '[:space:]' || echo 0)"
  apt_out="${apt_out:-0}"
  if [[ "${apt_out}" =~ ^[0-9]+$ ]] && [[ "$apt_out" -gt 0 ]]; then
    add_warn "доступно security-обновлений APT: ~$apt_out (apt-get upgrade)"
  else
    add_ok "security APT: обновлений не видно (simulated upgrade)"
  fi
fi

section "Постинг / health"
if curl -sf --max-time 8 http://127.0.0.1:8001/api/gdepar/health >/tmp/empire-audit-health.json 2>/dev/null; then
  add_ok "gdepar /api/gdepar/health отвечает"
else
  add_warn "gdepar health недоступен (empire_gdepar?)"
fi
for u in empire_main empire_gdepar empire_worker; do
  if systemctl is-active --quiet "$u" 2>/dev/null; then
    add_ok "unit $u active"
  else
    add_issue "unit $u не active"
  fi
done
stern_used="$ROOT/data/stern_technique_used.json"
stern_matrix="$ROOT/data/stern_technique_matrix_161_200.json"
if [[ -f "$stern_matrix" ]]; then
  ready_n="$(python3 -c "import json; d=json.load(open('$stern_matrix')); print(sum(1 for e in d.get('entries',[]) if e.get('status')=='ready'))")"
  used_n=0
  [[ -f "$stern_used" ]] && used_n="$(python3 -c "import json; print(len(json.load(open('$stern_used')).get('ids') or []))")"
  add_ok "Штерн видео-очередь: ~$((ready_n - used_n)) из $ready_n"
fi

section "Systemd empire-*"
failed_units="$(systemctl list-units 'empire*' --all --no-legend 2>/dev/null | awk '$3 != "active" && $3 != "inactive" && $2 == "loaded" && $1 != "empire-daily-audit.service" && $1 != "empire-night-pipeline.service" {print $1, $3}' || true)"
if [[ -n "$failed_units" ]]; then
  while IFS= read -r fu; do
    [[ -z "$fu" ]] && continue
    add_issue "unit $fu"
  done <<< "$failed_units"
else
  active_n="$(systemctl list-units 'empire*' --state=active --no-legend 2>/dev/null | wc -l | tr -d ' ')"
  add_ok "empire units active: $active_n"
fi

section "Итог"
status="OK"
if [[ "$ISSUES" -gt 0 ]]; then
  status="ISSUES"
elif [[ "$WARNINGS" -gt 0 ]]; then
  status="WARN"
fi
log "status=$status issues=$ISSUES warnings=$WARNINGS"
log "report=$REPORT"

# Telegram
if [[ -x "$ROOT/scripts/empire_daily_audit_notify.py" ]]; then
  "$ROOT/venv/bin/python" "$ROOT/scripts/empire_daily_audit_notify.py" \
    --status "$status" \
    --issues "$ISSUES" \
    --warnings "$WARNINGS" \
    --report "$REPORT" \
    ${TELEGRAM_LINES[@]+"${TELEGRAM_LINES[@]}"} || log "WARN: Telegram-уведомление не отправлено"
fi

# Хранить отчёты 30 дней
find "$LOG_DIR" -name 'daily-audit-*.log' -mtime +30 -delete 2>/dev/null || true

exit 0
