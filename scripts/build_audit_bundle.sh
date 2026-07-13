#!/usr/bin/env bash
# Сборка архива для полного аудита в Gemini.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/audit"
EXPORT="$OUT/gemini_export"

"$ROOT/scripts/export_gemini_tg_audit.sh"

cd "$OUT"
tar -czf gemini_full_audit_bundle_jul2026.tar.gz \
  gemini_export/ \
  gemini_PROMPT_FULL_AUDIT_JUL2026.txt \
  gemini_tg_channels_audit_prompt.md

echo "OK → $OUT/gemini_full_audit_bundle_jul2026.tar.gz"
ls -lh "$OUT/gemini_full_audit_bundle_jul2026.tar.gz"
