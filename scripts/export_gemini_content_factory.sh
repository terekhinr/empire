#!/usr/bin/env bash
# Сборка архива Content Factory для Gemini (Gdepar + Stern).
# Использование: ./scripts/export_gemini_content_factory.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXPORT="$ROOT/docs/content_factory/gemini_export"
ARCHIVE="$ROOT/docs/content_factory/gemini_content_factory_bundle.tar.gz"

cd "$ROOT"

# Полные матрицы и BATCH_MANIFEST
./venv/bin/python tools/build_content_factory_matrix.py

# Уже готовые посты Gdepar (не дублировать id)
if [[ -f data/gdepar_duo_curated.json ]]; then
  cp data/gdepar_duo_curated.json "$EXPORT/EXISTING_gdepar_duo.json"
fi

# Запросы на перегенерацию (новый чат Gemini)
./venv/bin/python tools/build_gemini_batch_requests.py

# Копировать промпты из корня content_factory если обновлялись
for f in gemini_GENERATE_gdepar.txt gemini_GENERATE_stern.txt gemini_QUALITY_REVIEW.txt; do
  [[ -f docs/content_factory/$f ]] && cp "docs/content_factory/$f" "$EXPORT/" 2>/dev/null || true
done

cd "$ROOT/docs/content_factory"
tar -czf gemini_content_factory_bundle.tar.gz -C gemini_export .

echo "OK → $ARCHIVE"
tar -tzf gemini_content_factory_bundle.tar.gz | head -30
echo "…"
tar -tzf gemini_content_factory_bundle.tar.gz | wc -l
echo "files total"
