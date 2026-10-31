#!/bin/bash
# Healthcheck: VDSina Reality + Aeza Reality + JustHost STO1 Reality + CDN WS.
# Алерт в Telegram через empire_notify.py при fail>=1.
set -euo pipefail
XRAY=${XRAY:-/usr/local/lib/empire-xray/xray}
U_VDS=${U_VDS:-18538cf4-2116-41e9-baac-22184549c152}
U_AEZA=${U_AEZA:-5f8e0a4d-7804-48b5-bf16-3d5ad09c99c3}
STO1_META=${STO1_META:-/root/empire-secrets/justhost-stockholm/meta.json}
STATE=/var/lib/empire-vpn-health
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
mkdir -p "$STATE" /var/log
ts=$(date -Is)
ok=0; fail=0; report=""

run_one() {
  local name="$1" port="$2" cfg="$3"
  pkill -f "$cfg" 2>/dev/null || true
  $XRAY run -c "$cfg" >/tmp/empire-hc-${name}.log 2>&1 &
  local pid=$!
  sleep 1
  local ip tg yt dc
  ip=$(curl -sS --max-time 15 -x "socks5h://127.0.0.1:$port" https://api.ipify.org 2>/dev/null || true)
  tg=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 -x "socks5h://127.0.0.1:$port" https://web.telegram.org 2>/dev/null || true)
  yt=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 -x "socks5h://127.0.0.1:$port" https://www.youtube.com/generate_204 2>/dev/null || true)
  # Telegram DC: голый HTTP даёт 404 — это норма (TCP до DC жив)
  dc=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 12 -x "socks5h://127.0.0.1:$port" http://149.154.167.51:80/ 2>/dev/null || true)
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  if [[ -n "$ip" && "$tg" == "200" && "$yt" == "204" && ( "$dc" == "200" || "$dc" == "404" ) ]]; then
    report+="OK $name -> $ip tg=$tg yt=$yt dc=$dc"$'\n'
    ok=$((ok+1))
    echo ok > "$STATE/$name"
  else
    report+="FAIL $name ip=${ip:-none} tg=${tg:-none} yt=${yt:-none} dc=${dc:-none}"$'\n'
    fail=$((fail+1))
    echo fail > "$STATE/$name"
  fi
}

# STO1 Reality params from secrets (pbk/sid/ip); UUID = same as VDSina user01 probe
STO1_IP=31.192.244.186
STO1_PBK=""
STO1_SID=3f436455
STO1_SNI=www.vk.com
if [[ -f "$STO1_META" ]]; then
  eval "$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print("STO1_IP="+m.get("ip","31.192.244.186")); print("STO1_PBK="+m.get("pbk","")); print("STO1_SID="+m.get("sid","3f436455")); print("STO1_SNI="+m.get("sni","www.vk.com"))' "$STO1_META")"
fi
U_STO1=${U_STO1:-$U_VDS}

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
cat > "$CFGDIR/sto1.json" <<EJSON
{"log":{"loglevel":"error"},"inbounds":[{"listen":"127.0.0.1","port":18204,"protocol":"socks","settings":{"udp":true}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"$STO1_IP","port":443,"users":[{"id":"$U_STO1","encryption":"none","flow":"xtls-rprx-vision"}]}]},"streamSettings":{"network":"tcp","security":"reality","realitySettings":{"serverName":"$STO1_SNI","fingerprint":"chrome","publicKey":"$STO1_PBK","shortId":"$STO1_SID"}}}]}
EJSON

run_one vds 18201 "$CFGDIR/vds.json"
run_one aeza 18202 "$CFGDIR/aeza.json"
run_one sto1 18204 "$CFGDIR/sto1.json"
run_one cdn 18203 "$CFGDIR/cdn.json"

echo "[$ts] ok=$ok fail=$fail" | tee -a /var/log/empire-vpn-health.log
printf '%s' "$report" | tee -a /var/log/empire-vpn-health.log

if [[ $fail -ge 1 ]]; then
  msg="Empire VPN ALERT $ts"$'\n'"$report"$'\n'"legs: vds/aeza/sto1/cdn"
  PY="$ROOT/venv/bin/python"
  [[ -x $PY ]] || PY=python3
  "$PY" "$ROOT/scripts/empire_notify.py" "$msg" >/dev/null 2>&1 || true
fi
exit 0
