#!/usr/bin/env bash
# Уведомление в Telegram при завершении каждой части TOX1.
set -uo pipefail
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG="${1:-/var/log/empire/tox1-upload-progress.log}"
PART="${2:-?}"
TOTAL="${3:-15}"
python3 - "$PART" "$TOTAL" "$LOG" <<'PY'
import sys
sys.path.insert(0, "/root/projects/empire/scripts")
import empire_notify as n
part, total, log = sys.argv[1], sys.argv[2], sys.argv[3]
n.send(f"✅ TOX1 часть {part}/{total} на Я.Диске\n📄 {log}")
PY
