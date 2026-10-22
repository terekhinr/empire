#!/bin/bash
set -euo pipefail
XRAY=${XRAY:-/usr/local/bin/xray}
U_VDS=${U_VDS:-18538cf4-2116-41e9-baac-22184549c152}
U_AEZA=${U_AEZA:-5f8e0a4d-7804-48b5-bf16-3d5ad09c99c3}
STATE=/var/lib/empire-vpn-health
mkdir -p "$STATE" /var/log
ts=$(date -Is)
ok=0; fail=0; report=""

run_one() {
  local name="$1" port="$2" cfg="$3"
  pkill -f "$cfg" 2>/dev/null || true
  $XRAY run -c "$cfg" >/tmp/empire-hc-${name}.log 2>&1 &
  local pid=$!
  sleep 1
  local ip tg yt
  ip=$(curl -sS --max-time 15 -x "socks5h://127.0.0.1:$port" https://api.ipify.org 2>/dev/null || true)
  tg=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 -x "socks5h://127.0.0.1:$port" https://web.telegram.org 2>/dev/null || true)
  yt=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 -x "socks5h://127.0.0.1:$port" https://www.youtube.com/generate_204 2>/dev/null || true)
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  if [[ -n "$ip" && "$tg" == "200" && "$yt" == "204" ]]; then
    report+="OK $name -> $ip tg=$tg yt=$yt"$'\n'
    ok=$((ok+1))
    echo ok > "$STATE/$name"
  else
    report+="FAIL $name ip=${ip:-none} tg=${tg:-none} yt=${yt:-none}"$'\n'
    fail=$((fail+1))
    echo fail > "$STATE/$name"
  fi
}

CFGDIR=/tmp/empire-vpn-hc
mkdir -p "$CFGDIR"
cat > "$CFGDIR/vds.json" <<EJSON
{"log":{"loglevel":"error"},"inbounds":[{"listen":"127.0.0.1","port":18201,"protocol":"socks","settings":{"udp":true}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"109.107.174.17","port":443,"users":[{"id":"$U_VDS","encryption":"none","flow":"xtls-rprx-vision"}]}]},"streamSettings":{"network":"tcp","security":"reality","realitySettings":{"serverName":"www.vk.com","fingerprint":"chrome","publicKey":"Ks4TJK3t-qNSEqTq0a3ExZpQur0C0or0CObQ5LMvrH4","shortId":"3f436455"}}}]}
EJSON
cat > "$CFGDIR/aeza.json" <<EJSON
{"log":{"loglevel":"error"},"inbounds":[{"listen":"127.0.0.1","port":18202,"protocol":"socks","settings":{"udp":true}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"138.124.90.47","port":443,"users":[{"id":"$U_AEZA","encryption":"none","flow":"xtls-rprx-vision"}]}]},"streamSettings":{"network":"tcp","security":"reality","realitySettings":{"serverName":"www.vk.com","fingerprint":"chrome","publicKey":"***REMOVED***","shortId":"1b74bb3a"}}}]}
EJSON
cat > "$CFGDIR/cdn.json" <<EJSON
{"log":{"loglevel":"error"},"inbounds":[{"listen":"127.0.0.1","port":18203,"protocol":"socks","settings":{"udp":true}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"vpn.kalitkuprikroy.ru","port":443,"users":[{"id":"$U_AEZA","encryption":"none"}]}]},"streamSettings":{"network":"ws","security":"tls","tlsSettings":{"serverName":"vpn.kalitkuprikroy.ru","fingerprint":"chrome","alpn":["http/1.1"]},"wsSettings":{"path":"/vless-ws-b3e91f2a/","host":"vpn.kalitkuprikroy.ru"}}}]}
EJSON

run_one vds 18201 "$CFGDIR/vds.json"
run_one aeza 18202 "$CFGDIR/aeza.json"
run_one cdn 18203 "$CFGDIR/cdn.json"

echo "[$ts] ok=$ok fail=$fail" | tee -a /var/log/empire-vpn-health.log
printf '%s' "$report" | tee -a /var/log/empire-vpn-health.log

if [[ $fail -ge 1 ]]; then
  msg="Empire VPN ALERT $ts"$'\n'"$report"
  if [[ -f /root/empire-secrets/telegram.env ]]; then
    set -a; source /root/empire-secrets/telegram.env; set +a
  fi
  if [[ -n "${EMPIRE_TG_BOT_TOKEN:-}" && -n "${EMPIRE_TG_CHAT_ID:-}" ]]; then
    curl -sS --max-time 10 -X POST "https://api.telegram.org/bot${EMPIRE_TG_BOT_TOKEN}/sendMessage" \
      -d chat_id="$EMPIRE_TG_CHAT_ID" --data-urlencode "text=$msg" >/dev/null || true
  fi
fi
exit 0
