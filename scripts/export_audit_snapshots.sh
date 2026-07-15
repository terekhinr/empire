#!/usr/bin/env bash
# Копирует KPI/финансы/инвентаризацию в docs/audit/exports/ — можно копировать из Cursor.
set -uo pipefail
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
OUT="$ROOT/docs/audit/exports"
STAMP="$(date +%Y-%m-%d)"
mkdir -p "$OUT"

copy_if() {
  local src="$1" dst="$2"
  [[ -f "$src" ]] && cp -a "$src" "$dst" && echo "  $dst"
}

echo "==> export audit snapshots ($STAMP)"
copy_if "$ROOT/data/empire_weekly_kpi.json" "$OUT/empire_weekly_kpi.json"
copy_if "$ROOT/data/empire_finance_ledger.json" "$OUT/empire_finance_ledger.json"
copy_if "$ROOT/data/infra/vps-software-inventory.txt" "$OUT/vps-software-inventory.txt"
copy_if "/var/log/empire/posting-metrics-latest.txt" "$OUT/posting-metrics-latest.txt"
copy_if "/var/log/empire/router-state.json" "$OUT/router-state.json"

# Markdown-сводка для копирования одним блоком (без TG и без рекурсии в yandex-sync)
EMPIRE_POSTING_METRICS_NO_TELEGRAM=1 EMPIRE_SKIP_YANDEX_AUDIT=1 \
  "$ROOT/venv/bin/python" "$ROOT/scripts/empire_weekly_posting_metrics.py" 2>/dev/null \
  | tee "$OUT/posting-weekly-$(date +%Y%m%d).txt" >/dev/null || true

cat > "$OUT/README.md" <<EOF
# Экспорт аудита (копируемые файлы)

Обновление: \`sudo bash scripts/export_audit_snapshots.sh\`

| Файл | Что |
|------|-----|
| empire_weekly_kpi.json | KPI постинга по неделям |
| empire_finance_ledger.json | Расходы/доходы |
| vps-software-inventory.txt | ПО на VPS |
| posting-metrics-latest.txt | Последний отчёт постинга |

Полный аудит: ../2026-07-15_FULL_INFRA_AUDIT.md  
Промпты Gemini: ../GEMINI_AUDIT_PROMPTS.md
EOF

echo "DONE → $OUT"
