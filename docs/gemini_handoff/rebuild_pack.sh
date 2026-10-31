#!/bin/bash
# Rebuild EMPIRE_FULL_CONTEXT_PACK.md for Gemini handoff
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/docs/gemini_handoff/EMPIRE_FULL_CONTEXT_PACK.md"
cd "$ROOT"

{
  echo "# Empire — полный контекст-пак для Gemini (сгенерировано $(date -u +%Y-%m-%dT%H:%MZ))"
  echo ""
  echo "> Приложение к \`docs/GEMINI_HANDOFF_CURSOR_EXIT_LOCAL_LLM_2026-10.md\`."
  echo "> Секреты не включены."
  echo ""
  echo "---"
  echo ""
} > "$OUT"

append() {
  local f="$1"
  if [[ -f "$f" ]]; then
    {
      echo ""
      echo "# ========== FILE: $f =========="
      echo ""
      cat "$f"
      echo ""
      echo ""
      echo "---"
    } >> "$OUT"
    echo "OK $f"
  else
    echo "MISS $f" >&2
  fi
}

append docs/PROJECT_OS.md
append docs/EMPIRE_PORTFOLIO_AUDIT_2026-07.md
append docs/EMPIRE_PIPELINE_CHECKLIST.md
append docs/empire_decisions_2026-05.md
append docs/empire_business_plan_2026.md
append docs/REMINDERS_gdepar.md
append docs/RESTORE_INDEX.md
append docs/pc_build_montage_llm_2026-07.md
append docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md
append docs/gdepar_ai_assistant_tz.md
append docs/pension_book_publish_tz.md
append docs/TZ_HOME_ASSISTANT.md
append docs/stern_kettlebell_ai_trainer_tz.md
append docs/garden_infoproduct_tz.md
append docs/gdepar_field_inspector_tz.md
append docs/gdepar_content_diversity_tz.md
append docs/career_tz_b2b_lead_bot_2026-10.md
append docs/pitch_autopost_product_tz_finmodel.md
append "docs/tz bot zhelenaya spina.txt"

{
  echo ""
  echo "# ========== FILE: docs/gdepar_checkpoints.md (first 220 lines) =========="
  echo ""
  head -n 220 docs/gdepar_checkpoints.md
  echo ""
  echo ""
  echo "---"
} >> "$OUT"

append docs/audit/20_PRODUCTS_FACTS_R7.md
append docs/audit/17_MILESTONES_R6_90D.md
append docs/metrika_goals_setup.md
append docs/cursor_vps_ssh_ru.md
append docs/HEALER_ARCHITECTURE.md
append docs/infra/README.md

ls -lh "$OUT"
wc -l "$OUT"
