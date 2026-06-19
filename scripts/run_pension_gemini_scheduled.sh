#!/usr/bin/env bash
# Запуск generate_pension_video_gemini.py с логом и отчётом.
set -euo pipefail
ROOT="/root/projects/empire"
LOG="$ROOT/data/pension/video/gemini_scheduled.log"
REPORT="$ROOT/data/pension/video/gemini_scheduled_report.txt"
PY="$ROOT/venv/bin/python3"
SCRIPT="$ROOT/scripts/generate_pension_video_gemini.py"
FINAL="$ROOT/data/pension/video/pension_4scenes_gemini.mp4"

exec >>"$LOG" 2>&1
echo "========== $(date -Iseconds) MSK=$(TZ=Europe/Moscow date -Iseconds) =========="

cd "$ROOT"
export PYTHONUNBUFFERED=1

if "$PY" "$SCRIPT"; then
  STATUS=OK
else
  STATUS=FAIL
fi

{
  echo "status: $STATUS"
  echo "finished_at_msk: $(TZ=Europe/Moscow date -Iseconds)"
  echo "log: $LOG"
  if [[ -f "$FINAL" ]]; then
    echo "final_video: $FINAL"
    echo "final_size_bytes: $(stat -c%s "$FINAL")"
    echo "final_duration: $(/root/projects/empire/venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2 -i "$FINAL" 2>&1 | grep Duration | head -1 || true)"
  else
    echo "final_video: (not created)"
  fi
  echo "--- last 40 log lines ---"
  tail -40 "$LOG"
} >"$REPORT"

echo "Report → $REPORT"

# Уведомление в Telegram админу
"$PY" "$ROOT/scripts/remind_pension_gemini_video.py" --kind done || true

exit $([[ "$STATUS" == OK ]] && echo 0 || echo 1)
