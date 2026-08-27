#!/bin/sh
# Торрент-сайты не открываются: ISP/DPI + sing-box DNS = NXDOMAIN.
# Лечение: домены трекеров → podkop FakeIP → VLESS (как YouTube).
# Раздача/качание пиров остаётся напрямую в WAN, не через VPS.
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

log() { printf '\033[1;32m[torrent-sites]\033[0m %s\n' "$*"; }

DOMAINS="rutracker.org www.rutracker.org rutracker.net rutracker.cc static.rutracker.cc feed.rutracker.cc rutracker.wiki bt.t-ru.org bt2.t-ru.org bt3.t-ru.org bt4.t-ru.org tr.t-ru.org rutor.info www.rutor.info nnmclub.to nnm-club.me nnmstatic.win kinozal.tv 1337x.to flibusta.is www.flibusta.is http.flibusta.is mobile.flibusta.is proxy.flibusta.is"

# файл со списка (если скрипт скачали с bootstrap)
if [ -f /etc/podkop/torrent-domains.txt ]; then
  DOMAINS="$(grep -v '^#' /etc/podkop/torrent-domains.txt | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
fi

[ -x /etc/init.d/podkop ] || { log "нет podkop"; exit 1; }

uci set podkop.main.user_domain_list_type='text'
CUR="$(uci -q get podkop.main.user_domains_text || true)"
PAD=" $CUR "
for d in $DOMAINS; do
  echo "$PAD" | grep -q " $d " && continue
  CUR="${CUR:+$CUR }$d"
  PAD=" $CUR "
done
uci set podkop.main.user_domains_text="$CUR"
uci commit podkop

rm -f /tmp/sing-box/cache.db
/etc/init.d/podkop restart
sleep 4
[ -x /etc/podkop/empire-lan-fix.sh ] && /etc/podkop/empire-lan-fix.sh >/dev/null 2>&1 || true
sleep 2

log "DNS rutracker (ожидаем 198.18.x):"
nslookup rutracker.org 127.0.0.1 2>&1 | head -8
log "HTTPS:"
curl -4 -sI -m 15 https://rutracker.org/ 2>&1 | head -5 || true
log "готово — с ПК: Ctrl+F5 на rutracker.org"
