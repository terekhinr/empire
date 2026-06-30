#!/bin/sh
# Full A/B: SKeen (VLESS) vs nfqws2 (MTS DPI) on Keenetic.
set -eu
ROOT=/root/projects/empire/scripts/keenetic-xkeen
ARM=100.80.133.85
ROUTER=192.168.1.1
ROUTER_PORT=222
PASS="${KEENETIC_ROUTER_PASS:-keenetic}"
BASE="http://193.233.232.48:8787"
REPORT=/tmp/youtube-ab-$(date +%Y%m%d%H%M%S)
mkdir -p "$(dirname "$REPORT")"

router_sh() {
  sshpass -p "$PASS" ssh -T -o ConnectTimeout=25 -o StrictHostKeyChecking=no \
    root@"$ARM" \
    "sshpass -p '$PASS' ssh -T -o ConnectTimeout=20 -o StrictHostKeyChecking=no -p $ROUTER_PORT root@$ROUTER '$1'"
}

log() { echo "$*" | tee -a "$REPORT"; }

router_probe() {
  router_sh 'export PATH=/opt/bin:/opt/sbin:$PATH
for u in https://www.youtube.com https://www.google.com/generate_204 https://ya.ru; do
  code=$(curl -4 -o /dev/null -s -w "%{http_code}" --connect-timeout 12 --max-time 20 "$u" 2>/dev/null || echo ERR)
  echo "curl $u -> $code"
done
echo nfqws2=$(pgrep nfqws2 || echo OFF)
echo skeen=$(pgrep skeen-box || echo OFF)
echo nfqueue=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)
echo quic=$(iptables-save 2>/dev/null | grep "udp dpt:443" | grep -c DROP || echo 0)
err=$(grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0)
yt=$(grep -c "outbound multiplex connection to www.youtube.com" /opt/var/log/sing-box.log 2>/dev/null || echo 0)
echo log_errors=$err youtube_mux_ok=$yt'
}

vps_wan_test() {
  if sh "$ROOT/vps-youtube-test.sh" >/tmp/vps-test-$$.txt 2>&1; then
    log "VPS_WAN=OK $(tr '\n' ' ' </tmp/vps-test-$$.txt)"
    return 0
  fi
  log "VPS_WAN=FAIL $(tr '\n' ' ' </tmp/vps-test-$$.txt)"
  return 1
}

deploy() {
  script="$1"
  log "DEPLOY $script"
  router_sh "curl -fsSL $BASE/$script | sh" >>"$REPORT" 2>&1 || log "DEPLOY_FAIL $script"
  sleep 12
}

score_probe() {
  probe_out=$(router_probe 2>&1) || probe_out="PROBE_FAIL"
  echo "$probe_out" >>"$REPORT"
  yt_ok=$(echo "$probe_out" | grep -c 'curl https://www.youtube.com -> 200' || true)
  g_ok=$(echo "$probe_out" | grep -c 'curl https://www.google.com/generate_204 -> 204' || true)
  ya_ok=$(echo "$probe_out" | grep -c 'curl https://ya.ru -> 200' || true)
  mux=$(echo "$probe_out" | sed -n 's/.*youtube_mux_ok=\([0-9]*\).*/\1/p' | tail -1)
  mux=${mux:-0}
  score=$((yt_ok * 40 + g_ok * 20 + ya_ok * 20 + (mux > 0 ? 20 : 0)))
  log "SCORE=$score yt=$yt_ok g204=$g_ok ya=$ya_ok mux=$mux"
  echo "$score"
}

log "=== A/B BENCHMARK $(date -Is) ==="
vps_wan_test || true

log ""
log "=== A: SKeen + VLESS (52-youtube-stable) ==="
deploy "52-youtube-stable.sh"
score_a=$(score_probe)

log ""
log "=== B: nfqws2 unified MTS (32-nfqws2-unified-youtube) ==="
router_sh '/opt/bin/skeen stop 2>/dev/null; killall skeen-box 2>/dev/null; true' >>"$REPORT" 2>&1 || true
sleep 3
deploy "32-nfqws2-unified-youtube.sh"
score_b=$(score_probe)

log ""
log "=== C: nfqws2 split CUSTOM googlevideo (apply mts.conf) ==="
router_sh "curl -fL -o /opt/etc/nfqws2/nfqws2.conf $BASE/nfqws2-mts.conf && /opt/etc/init.d/S51nfqws2 restart && sleep 4 && /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null; iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP; conntrack -F 2>/dev/null || true" >>"$REPORT" 2>&1 || true
sleep 8
score_c=$(score_probe)

log ""
log "=== WINNER selection ==="
best=0
winner="none"
score_a=${score_a:-0}
score_b=${score_b:-0}
score_c=${score_c:-0}
log "candidate A score=$score_a"
log "candidate B score=$score_b"
log "candidate C score=$score_c"
if [ "$score_a" -gt "$best" ]; then best=$score_a; winner=A; fi
if [ "$score_b" -gt "$best" ]; then best=$score_b; winner=B; fi
if [ "$score_c" -gt "$best" ]; then best=$score_c; winner=C; fi
log "BEST=$winner SCORE=$best"

if [ "$winner" = "A" ]; then
  deploy "52-youtube-stable.sh"
elif [ "$winner" = "B" ]; then
  deploy "32-nfqws2-unified-youtube.sh"
else
  router_sh "curl -fL -o /opt/etc/nfqws2/nfqws2.conf $BASE/nfqws2-mts.conf && /opt/etc/init.d/S51nfqws2 restart" >>"$REPORT" 2>&1 || true
fi

log ""
log "=== FINAL STATE ==="
router_probe >>"$REPORT" 2>&1 || true
vps_wan_test || true
log "REPORT_FILE=$REPORT"
cat "$REPORT"
