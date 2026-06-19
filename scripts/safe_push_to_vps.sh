#!/usr/bin/env bash
# Безопасная выкладка с ПК на VPS: НЕ трогает main.py и другие «тяжёлые» ядра без явного флага.
#
# На ПК (из корня клона Empire):
#   EMPIRE_VPS=root@moderate-amethys ./scripts/safe_push_to_vps.sh
#   EMPIRE_VPS=root@moderate-amethys ./scripts/safe_push_to_vps.sh --with-core
#
# По умолчанию: content_config, data/, docs/, gdepar_content.py, deploy-конфиги.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VPS="${EMPIRE_VPS:-root@moderate-amethys}"
REMOTE="${EMPIRE_REMOTE_DIR:-/root/projects/empire}"
WITH_CORE=0
DRY=0

for arg in "$@"; do
  case "$arg" in
    --with-core) WITH_CORE=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

RSYNC=(rsync -avz --progress)
EXCLUDES=(
  --exclude venv/
  --exclude __pycache__/
  --exclude .git/
  --exclude .env
  --exclude '*.db'
  --exclude '*.db-wal'
  --exclude '*.db-shm'
  --exclude media/
  --exclude vector_db/
  --exclude .cursor/
)

if [[ "$WITH_CORE" -eq 0 ]]; then
  EXCLUDES+=(
    --exclude main.py
    --exclude gdepar_app.py
    --exclude dashboard.py
    --exclude web_app.py
    --exclude empire_worker.py
  )
  echo "Режим: data/config/docs (без ядра). Для main.py: --with-core + проверка размера."
else
  echo "Режим: --with-core (включая main.py) — проверяю локальные файлы..."
  "$ROOT/scripts/guard_critical_files.sh"
fi

PATHS=(
  content_config.json
  data/
  docs/
  gdepar_content.py
  gdepar_book_rubrics.py
  deploy/
  scripts/guard_critical_files.sh
  scripts/safe_push_to_vps.sh
)

if [[ "$WITH_CORE" -eq 1 ]]; then
  PATHS+=(main.py gdepar_app.py dashboard.py web_app.py empire_worker.py)
fi

CMD=("${RSYNC[@]}" "${EXCLUDES[@]}" "${PATHS[@]}" "${VPS}:${REMOTE}/")
if [[ "$DRY" -eq 1 ]]; then
  echo "DRY RUN: ${CMD[*]}"
  exit 0
fi

"${CMD[@]}"

echo "==> guard на VPS"
ssh "$VPS" "$REMOTE/scripts/guard_critical_files.sh"

echo "OK: safe push завершён. Перезапуск при необходимости:"
echo "  ssh $VPS 'systemctl restart empire_main'  # только если меняли main.py"
