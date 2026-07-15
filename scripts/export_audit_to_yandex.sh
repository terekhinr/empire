#!/usr/bin/env bash
# Аудит Empire → Яндекс.Диск (без ручного копирования).
# Путь на Диске: obsidian (2)/Empire/audit/  — видно в клиенте Яндекс на ПК.
set -euo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

REMOTE="${RCLONE_REMOTE:-yandex}"
VAULT="${RCLONE_VAULT_REMOTE_PATH:-obsidian (2)}"
DEST="${YANDEX_AUDIT_REMOTE_PATH:-${VAULT}/Empire/audit}"
STAGING="${ROOT}/.audit-yandex-staging"
LOG="${EMPIRE_LOG_DIR:-/var/log/empire}/audit-yandex-sync.log"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

if ! command -v rclone >/dev/null 2>&1; then
  log "ERROR: rclone не установлен"
  exit 1
fi
if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
  log "ERROR: remote ${REMOTE} не настроен"
  exit 1
fi

# Свежие снимки в docs/audit/exports/
if [[ -x "$ROOT/scripts/export_audit_snapshots.sh" ]]; then
  bash "$ROOT/scripts/export_audit_snapshots.sh" >>"$LOG" 2>&1 || log "WARN: export_audit_snapshots"
fi

rm -rf "$STAGING"
mkdir -p "$STAGING/exports" "$STAGING/docs"

# exports/
cp -a "$ROOT/docs/audit/exports/." "$STAGING/exports/" 2>/dev/null || true

# главные доки аудита
for f in \
  "$ROOT/docs/audit/2026-07-15_STATUS_SLICE.md" \
  "$ROOT/docs/audit/2026-07-15_FULL_INFRA_AUDIT.md" \
  "$ROOT/docs/audit/GEMINI_AUDIT_PROMPTS.md" \
  "$ROOT/docs/infra/ARCHITECTURE.md" \
  "$ROOT/docs/EMPIRE_PIPELINE_CHECKLIST.md" \
  "$ROOT/docs/empire_business_plan_2026.md"; do
  [[ -f "$f" ]] && cp -a "$f" "$STAGING/docs/$(basename "$f")"
done

# KPI/финансы из data (если есть)
[[ -f "$ROOT/data/empire_weekly_kpi.json" ]] && \
  cp -a "$ROOT/data/empire_weekly_kpi.json" "$STAGING/exports/"
[[ -f "$ROOT/data/empire_finance_ledger.json" ]] && \
  cp -a "$ROOT/data/empire_finance_ledger.json" "$STAGING/exports/"

# последние логи (короткие)
for lf in posting-metrics-latest.txt daily-audit-latest.log; do
  [[ -f "/var/log/empire/$lf" ]] && cp -a "/var/log/empire/$lf" "$STAGING/exports/" 2>/dev/null || true
done
[[ -f /var/log/empire/router-state.json ]] && \
  cp -a /var/log/empire/router-state.json "$STAGING/exports/"

cat > "$STAGING/README_YANDEX.txt" <<EOF
Empire audit — автовыгрузка с VPS
Обновлено: $(date -Iseconds)
Путь на VPS: $ROOT/docs/audit/exports/

На ПК: Яндекс.Диск → obsidian (2) → Empire → audit

Обновить вручную на VPS:
  sudo bash scripts/export_audit_to_yandex.sh

Авто: утренний бриф empire-morning-brief (~07:05 МСК) + еженедельный KPI.
EOF

log "sync → ${REMOTE}:${DEST}"
rclone copy "$STAGING" "${REMOTE}:${DEST}" \
  --fast-list \
  -v 2>>"$LOG"

# Симлинк latest в exports для удобства
rclone copy "$STAGING" "${REMOTE}:${DEST}/latest" \
  --fast-list 2>>"$LOG" || true

log "DONE ${REMOTE}:${DEST}"
rclone lsf "${REMOTE}:${DEST}/" --dirs-only 2>/dev/null | head -5 | while read -r d; do
  log "  на Диске: $d"
done
