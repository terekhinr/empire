#!/bin/sh
# Windsurf / Codeium — в РФ часто режется; гоним через VLESS (podkop user_domains).
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

# windsurf.dev — демо v0.dev (кнопки-заглушки). Реальный продукт: windsurf.com / codeium.com
DOMAINS="windsurf.com www.windsurf.com auth.windsurf.com auth.codeium.com codeium.com www.codeium.com api.codeium.com server.codeium.com marketplace.codeium.com windsurf.dev www.windsurf.dev codeiumusercontent.com staging.windsurf.app"

[ -x /etc/init.d/podkop ] || { echo "нет podkop"; exit 1; }

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

/usr/bin/podkop list_update 2>/dev/null || /etc/init.d/podkop reload 2>/dev/null || true
sleep 5
[ -x /usr/sbin/empire-singbox-mark ] && /usr/sbin/empire-singbox-mark
[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch

echo "DNS:"
nslookup www.windsurf.dev 127.0.0.1 2>&1 | grep Address | tail -2
curl -4 -s -o /dev/null -w "https://www.windsurf.dev/ → %{http_code}\n" --connect-timeout 12 https://www.windsurf.dev/
