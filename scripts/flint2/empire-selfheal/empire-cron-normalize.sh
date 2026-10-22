#!/bin/sh
# Сводит /etc/crontabs/root к одному каноническому набору empire-задач.
# Паттерн как у OpenWrt/monit: один scheduler, без thrashing.
set -eu

CRON="${1:-/etc/crontabs/root}"
TMP="$(mktemp)"
MARK="# empire-selfheal-managed"

# Не-empire строки (уникальные) + комментарии disabled
awk '
  BEGIN { keep=0 }
  /^[[:space:]]*$/ { next }
  /^# DISABLED empire:/ {
    if (!seen_disabled[$0]++) print
    next
  }
  /^#/ { next }
  /empire-flint-watchdog|empire-lan-watch|empire-ha-healer|empire-dns-ai-tunnel|fix-table100|enforce-vless-ssh|flint2-tunnel\/start|podkop list_update/ {
    next
  }
  {
    if (!seen[$0]++) print
  }
' "$CRON" >"$TMP" 2>/dev/null || : >"$TMP"

{
  echo "$MARK"
  echo '*/10 * * * * /etc/flint2-tunnel/start.sh'
  echo '*/5 * * * * /etc/empire/fix-table100.sh'
  echo '* * * * * /etc/empire/enforce-vless-ssh.sh'
  echo '* * * * * flock -n /var/lock/empire-heal.lock /etc/podkop/empire-lan-watch.sh'
  echo '*/5 * * * * flock -n /var/lock/empire-heal.lock /usr/sbin/empire-flint-watchdog >/dev/null 2>&1'
  echo '*/5 * * * * flock -n /var/lock/empire-heal.lock /usr/sbin/empire-awg-failover ensure >/dev/null 2>&1'
  echo '*/5 * * * * /usr/sbin/empire-ha-healer >/dev/null 2>&1'
  echo '* * * * * /etc/empire/empire-dns-ai-tunnel.sh'
  echo '13 9 * * * /usr/bin/podkop list_update'
} >>"$TMP"

# Сохраняем DISABLED empire комментарий если был
if grep -q '^# DISABLED empire:' "$CRON" 2>/dev/null; then
  grep '^# DISABLED empire:' "$CRON" | awk '!seen[$0]++' >>"$TMP"
fi

# Дедуп всего файла на всякий случай
awk '!seen[$0]++' "$TMP" >"${TMP}.u"
mv "${TMP}.u" "$CRON"
rm -f "$TMP"
chmod 600 "$CRON" 2>/dev/null || true

/etc/init.d/cron restart >/dev/null 2>&1 || true
echo "OK cron lines=$(wc -l <"$CRON")"
