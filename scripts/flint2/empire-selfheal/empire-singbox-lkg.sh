#!/bin/sh
# Last-Known-Good для sing-box (паттерн OpenWrt UCI apply/confirm/rollback).
# НЕ вызывает podkop restart — только копирует golden и рестартит sing-box.
# Использование: empire-singbox-lkg.sh restore|save|smoke|ensure
set -eu

CFG=/etc/sing-box/config.json
GOLD=/etc/podkop/sing-box.golden.json
LKG=/etc/podkop/sing-box.lkg.json
LOG=/tmp/empire-singbox-lkg.log
LOCK=/var/lock/empire-heal.lock

log() { echo "$(date -Is 2>/dev/null || date) $*" >>"$LOG"; }

dns_fakeip() {
  d="$1"
  ip=$(nslookup "$d" 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
  case "$ip" in
    198.18.*) return 0 ;;
  esac
  return 1
}

smoke() {
  # sing-box жив + FakeIP для TG/YT/AI + HTTP smoke
  pgrep -f '/usr/bin/sing-box run' >/dev/null 2>&1 || return 1
  sing-box check -c "$CFG" >/dev/null 2>&1 || return 1
  grep -q 'ai_awg-user-domains-ruleset' "$CFG" 2>/dev/null || return 1
  dns_fakeip telegram.org || return 1
  dns_fakeip youtube.com || return 1
  dns_fakeip chatgpt.com || dns_fakeip api2.cursor.sh || return 1
  code=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 12 \
    https://web.telegram.org/ 2>/dev/null || echo 000)
  case "$code" in 200|301|302) ;; *) return 1 ;; esac
  code2=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 8 --max-time 12 \
    https://www.youtube.com/generate_204 2>/dev/null || echo 000)
  [ "$code2" = "204" ] || [ "$code2" = "200" ] || return 1
  return 0
}

save() {
  [ -f "$CFG" ] || return 1
  sing-box check -c "$CFG" >/dev/null 2>&1 || return 1
  grep -q 'ai_awg-user-domains-ruleset' "$CFG" 2>/dev/null || return 1
  smoke || return 1
  cp -a "$CFG" "$GOLD"
  cp -a "$CFG" "$LKG"
  chmod 600 "$GOLD" "$LKG" 2>/dev/null || true
  log "SAVE golden+lkg ok"
  return 0
}

restore() {
  src=""
  if [ -f "$GOLD" ] && sing-box check -c "$GOLD" >/dev/null 2>&1; then
    src="$GOLD"
  elif [ -f "$LKG" ] && sing-box check -c "$LKG" >/dev/null 2>&1; then
    src="$LKG"
  else
    log "RESTORE no valid golden/lkg"
    return 1
  fi
  cp -a "$src" "$CFG"
  if command -v jq >/dev/null 2>&1; then
    jq '.route.default_mark = 2097152' "$CFG" >/tmp/sb-lkg-mark.json 2>/dev/null \
      && mv /tmp/sb-lkg-mark.json "$CFG" || true
  fi
  # Prefer sing-box restart; avoid podkop regenerate (race → duplicate rule-set tags)
  /etc/init.d/sing-box restart >/dev/null 2>&1 || {
    killall sing-box 2>/dev/null || true
    /usr/bin/sing-box run -c "$CFG" -D /usr/share/sing-box >/dev/null 2>&1 &
  }
  sleep 3
  [ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch >/dev/null 2>&1 || true
  [ -x /etc/podkop/empire-lan-fix.sh ] && /etc/podkop/empire-lan-fix.sh >/dev/null 2>&1 || true
  log "RESTORE from $src"
  return 0
}

config_ok() {
  pgrep -f '/usr/bin/sing-box run' >/dev/null 2>&1 || return 1
  sing-box check -c "$CFG" >/dev/null 2>&1 || return 1
  grep -q 'ai_awg-user-domains-ruleset' "$CFG" 2>/dev/null || return 1
  dns_fakeip telegram.org || return 1
  dns_fakeip youtube.com || return 1
  dns_fakeip chatgpt.com || dns_fakeip api2.cursor.sh || return 1
  return 0
}

ensure() {
  if smoke; then
    # периодически обновляем LKG только если всё зелёное
    save >/dev/null 2>&1 || true
    return 0
  fi
  # Конфиг и FakeIP живы, а HTTP мёртв — это путь до VPS, не битый json.
  # Рестарт sing-box тут только роняет DNS на несколько секунд.
  if config_ok; then
    log "ENSURE skip restore: config+FakeIP ok, HTTP fail (upstream)"
    return 1
  fi
  now=$(date +%s)
  last=0
  [ -f /tmp/empire-lkg-restore.ts ] && last=$(cat /tmp/empire-lkg-restore.ts 2>/dev/null || echo 0)
  if [ $((now - last)) -lt 900 ]; then
    log "ENSURE skip restore: cooldown"
    return 1
  fi
  echo "$now" >/tmp/empire-lkg-restore.ts
  log "ENSURE smoke FAIL → restore"
  restore || return 1
  sleep 2
  if smoke; then
    log "ENSURE OK after restore"
    save >/dev/null 2>&1 || true
    return 0
  fi
  log "ENSURE STILL BAD after restore"
  return 1
}

cmd="${1:-ensure}"
case "$cmd" in
  smoke) smoke ;;
  save) save ;;
  restore) restore ;;
  ensure)
    # Внешний flock из cron; если вызвали вручную — берём lock сами
    if [ -n "${EMPIRE_HEAL_LOCKED:-}" ]; then
      ensure
    else
      flock -n "$LOCK" env EMPIRE_HEAL_LOCKED=1 "$0" ensure
    fi
    ;;
  *)
    echo "usage: $0 smoke|save|restore|ensure" >&2
    exit 2
    ;;
esac
