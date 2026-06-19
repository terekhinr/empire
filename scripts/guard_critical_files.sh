#!/usr/bin/env bash
# Блокирует старт/деплой, если критичные файлы пустые или подозрительно малы.
# Использование: ./scripts/guard_critical_files.sh [--warn]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WARN_ONLY=0
[[ "${1:-}" == "--warn" ]] && WARN_ONLY=1

fail() {
  if [[ "$WARN_ONLY" -eq 1 ]]; then
    echo "WARN guard_critical_files: $*" >&2
    exit 0
  fi
  echo "ERROR guard_critical_files: $*" >&2
  exit 1
}

check_min_bytes() {
  local rel="$1" min="$2"
  local path="$ROOT/$rel"
  if [[ ! -f "$path" ]]; then
    fail "missing $rel"
  fi
  local size
  size="$(wc -c <"$path" | tr -d ' ')"
  if [[ "$size" -lt "$min" ]]; then
    fail "$rel is $size bytes (min $min) — похоже на обнуление/не тот файл"
  fi
}

# rel_path min_bytes
checks=(
  "main.py 100000"
  "gdepar_app.py 50000"
  "dashboard.py 5000"
  "web_app.py 3000"
  "empire_worker.py 3000"
  "gdepar_content.py 10000"
  "content_config.json 5000"
)

for item in "${checks[@]}"; do
  read -r rel min <<<"$item"
  check_min_bytes "$rel" "$min"
done

# main.py должен содержать оркестратор
if ! grep -q 'Оркестратор запущен\|async def main' "$ROOT/main.py" 2>/dev/null; then
  fail "main.py не похож на оркестратор (нет async def main / маркера запуска)"
fi

exit 0
