#!/bin/sh
# Проверка YouTube и «заблокированных» сервисов после podkop/zapret2.
set -eu

log() { printf '\033[1;32m[verify]\033[0m %s\n' "$*"; }
fail=0

check() {
  name="$1"
  url="$2"
  if curl -fsSIL --max-time 15 "$url" 2>/dev/null | head -1 | grep -qE '200|301|302'; then
    log "OK  $name"
  else
    log "FAIL $name ($url)"
    fail=1
  fi
}

log "DNS..."
nslookup youtube.com 127.0.0.1 >/dev/null 2>&1 || nslookup youtube.com >/dev/null 2>&1 || log "DNS lookup warning"

check "YouTube" "https://www.youtube.com/"
check "Google" "https://www.google.com/"
check "Sber" "https://www.sberbank.ru/"

if command -v podkop >/dev/null 2>&1 || [ -x /etc/init.d/podkop ]; then
  /etc/init.d/podkop status 2>/dev/null || true
fi

if [ -x /etc/init.d/zapret2 ]; then
  /etc/init.d/zapret2 status 2>/dev/null || true
fi

[ "$fail" -eq 0 ] && log "все проверки прошли" || log "есть ошибки — см. logread и LuCI Podkop/Zapret2"
exit "$fail"
