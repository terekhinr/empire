#!/bin/sh
# Держит DNS так, чтобы Cursor/Claude/OpenAI/Gemini шли в podkop FakeIP → awg0.
# Обход 1.1.1.1 разрешён ТОЛЬКО для CDN видео YouTube.
# Ставится на Flint: /etc/empire/empire-dns-ai-tunnel.sh + cron.
set -eu

CONF_ETC=/etc/dnsmasq.d/99-cursor-bypass.conf
CONF_TMP=/tmp/dnsmasq.d/99-cursor-bypass.conf
GOLDEN='# Empire DNS: AI stays on FakeIP/awg0. Only YouTube video CDN bypass.
# DO NOT add cursor.com / claude.ai / anthropic.com / openai.com / chatgpt.com here.
server=/googlevideo.com/1.1.1.1
server=/jnn-pa.googleapis.com/1.1.1.1
'

mkdir -p /etc/dnsmasq.d /tmp/dnsmasq.d

need_write=0
for f in "$CONF_ETC" "$CONF_TMP"; do
  if [ ! -f "$f" ] || ! grep -q 'googlevideo.com/1.1.1.1' "$f" 2>/dev/null \
     || grep -Eq '^server=/(cursor\.|anthropic\.com|openai\.com|claude\.ai|chatgpt\.com)' "$f" 2>/dev/null; then
    need_write=1
    break
  fi
done

if [ "$need_write" -eq 1 ]; then
  printf '%s' "$GOLDEN" >"$CONF_ETC"
  cp -a "$CONF_ETC" "$CONF_TMP"
  killall -HUP dnsmasq 2>/dev/null || true
fi
