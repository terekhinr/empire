#!/usr/bin/env bash
# Освежить rating_avg / reviews_total по уже привязанным к Яндексу точкам (только где reviews_total пусто/0).
# Регионы: MO, SPB, MSK (лимиты env BANYA_REFRESH_MO_LIMIT, BANYA_REFRESH_SPB_LIMIT, BANYA_REFRESH_MSK_LIMIT).
# Запуск из корня проекта: bash tools/parsers/_run_refresh_mo_spb.sh
set -euo pipefail
export HOME="${HOME:-/root}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/root/.cache/ms-playwright}"
export PYTHONUNBUFFERED=1
# Пауза между точками в refresh (анти-CAPTCHA): по умолчанию 8–15 с, см. BANYA_REFRESH_WAIT_MIN / BANYA_REFRESH_WAIT_MAX
cd "$(dirname "$0")/../.."
MO_LIM="${BANYA_REFRESH_MO_LIMIT:-200}"
SPB_LIM="${BANYA_REFRESH_SPB_LIMIT:-120}"
MSK_LIM="${BANYA_REFRESH_MSK_LIMIT:-20}"
LOG="${BANYA_REFRESH_LOG:-logs/banya_refresh_mo_spb.log}"
mkdir -p logs
exec >>"$LOG" 2>&1
echo "=== refresh batch $(date -Is) MO limit=$MO_LIM need-reviews ==="
./venv/bin/python -u tools/parsers/yandex_scrape.py refresh --region MO --limit "$MO_LIM" --need-reviews
echo "=== refresh SPB limit=$SPB_LIM need-reviews ==="
./venv/bin/python -u tools/parsers/yandex_scrape.py refresh --region SPB --limit "$SPB_LIM" --need-reviews
echo "=== refresh MSK limit=$MSK_LIM need-reviews ==="
./venv/bin/python -u tools/parsers/yandex_scrape.py refresh --region MSK --limit "$MSK_LIM" --need-reviews
echo "=== done $(date -Is) ==="
