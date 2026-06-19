#!/usr/bin/env bash
# Пакетный enrich МО → СПб последовательно одним процессом.
# Лог: /root/projects/empire/logs/banya_enrich_$(date +%F_%H%M).log
set -u
cd /root/projects/empire || exit 1
LOG="logs/banya_enrich_$(date +%F_%H%M).log"
export PYTHONUNBUFFERED=1
{
    echo "=== batch enrich start: $(date '+%F %T') ==="
    echo ""
    echo "### MO (164 spots, ~25–35 min)"
    venv/bin/python -u tools/parsers/yandex_scrape.py enrich --region MO --limit 300 2>&1

    echo ""
    echo "### SPB (118 spots, ~20–25 min)"
    venv/bin/python -u tools/parsers/yandex_scrape.py enrich --region SPB --limit 300 2>&1

    echo ""
    echo "=== batch enrich done: $(date '+%F %T') ==="
} >>"$LOG" 2>&1
