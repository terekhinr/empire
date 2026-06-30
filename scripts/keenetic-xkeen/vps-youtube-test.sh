#!/bin/sh
# Автотест YouTube через VLESS. Exit 0 = OK.
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
PORT=8443
SOCK=10820
CFG=/tmp/youtube-test-$$.json
FAIL=0
ADDR="${VPS_TEST_ADDR:-127.0.0.1}"

cat >"$CFG" <<EOF
{"log":{"loglevel":"error"},"inbounds":[{"listen":"127.0.0.1","port":$SOCK,"protocol":"socks","settings":{"udp":true}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"$ADDR","port":$PORT,"users":[{"id":"19dd1a1d-a8a1-40ea-a977-121c0a01ddf6","encryption":"none"}]}]},"streamSettings":{"network":"tcp","security":"reality","realitySettings":{"serverName":"www.microsoft.com","publicKey":"***REMOVED***","shortId":"1b74bb3a","fingerprint":"chrome"}}}]}
EOF

pkill -f "$CFG" 2>/dev/null || true
timeout 20 xray run -c "$CFG" >/dev/null 2>&1 &
xp=$!
sleep 2

check() {
  url="$1"
  name="$2"
  if curl -sfI --connect-timeout 12 -x socks5h://127.0.0.1:$SOCK "$url" 2>/dev/null | head -1 | grep -qE '200|204|301|302'; then
    echo "OK $name"
  else
    echo "FAIL $name"
    FAIL=1
  fi
}

check "https://www.youtube.com" "youtube"
check "https://www.google.com/generate_204" "gstatic204"

kill "$xp" 2>/dev/null || true
wait "$xp" 2>/dev/null || true
rm -f "$CFG"
exit $FAIL
