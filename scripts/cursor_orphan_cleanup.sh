#!/bin/bash
# Убирает «зомби» Cursor extensionHost/fileWatcher после переподключений Remote SSH.
set -euo pipefail

log() { echo "[$(date -Iseconds)] cursor_cleanup: $*"; }

freed=0
mapfile -t EHS < <(pgrep -af 'bootstrap-fork --type=extensionHost' 2>/dev/null | awk '{print $1}' || true)
mapfile -t FWS < <(pgrep -af 'bootstrap-fork --type=fileWatcher' 2>/dev/null | awk '{print $1}' || true)

eh_age_sec() {
  ps -p "$1" -o etimes= 2>/dev/null | tr -d ' ' || echo 999999
}

if ((${#EHS[@]} > 1)); then
  keep_eh="${EHS[-1]}"
  keep_age=$(eh_age_sec "$keep_eh")
  for pid in "${EHS[@]}"; do
    [[ "$pid" == "$keep_eh" ]] && continue
    age=$(eh_age_sec "$pid")
    # Убиваем только если старый EH живёт дольше 2 мин (не момент handoff).
    if [ "$age" -le 120 ]; then
      log "skip young extensionHost pid=$pid age=${age}s"
      continue
    fi
    rss_kb=$(awk '/^Rss:/ {print $2}' /proc/"$pid"/smaps_rollup 2>/dev/null || echo 0)
    log "killing stale extensionHost pid=$pid age=${age}s rss_kb=$rss_kb (keep=$keep_eh age=${keep_age}s)"
    kill "$pid" 2>/dev/null || true
    freed=$((freed + rss_kb))
  done
elif ((${#EHS[@]} == 1)); then
  log "extensionHost count=1"
else
  log "extensionHost count=0"
fi

if ((${#FWS[@]} > 1)); then
  keep_fw="${FWS[-1]}"
  for pid in "${FWS[@]}"; do
    [[ "$pid" == "$keep_fw" ]] && continue
    rss_kb=$(awk '/^Rss:/ {print $2}' /proc/"$pid"/smaps_rollup 2>/dev/null || echo 0)
    log "killing extra fileWatcher pid=$pid rss_kb=$rss_kb (keep=$keep_fw)"
    kill "$pid" 2>/dev/null || true
    freed=$((freed + rss_kb))
  done
fi

sleep 1
pgrep -af 'json-language-features.*node-ipc|markdown-language-features.*node-ipc' 2>/dev/null | while read -r line; do
  pid=$(echo "$line" | awk '{print $1}')
  ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  if [[ -n "${ppid:-}" ]] && ! kill -0 "$ppid" 2>/dev/null; then
    log "killing orphan lang-server pid=$pid"
    kill "$pid" 2>/dev/null || true
  fi
done

log "done; freed ~$((freed / 1024)) MB RSS"
