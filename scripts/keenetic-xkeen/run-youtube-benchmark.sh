#!/bin/sh
# Benchmark YouTube strategies: VPS WAN + router deploy + log analysis.
set -eu
ROOT=/root/projects/empire/scripts/keenetic-xkeen
ARM=100.80.133.85
ROUTER=192.168.1.1
ROUTER_PORT=222
PASS="${KEENETIC_ROUTER_PASS:-keenetic}"
BASE="http://127.0.0.1:8787"
REPORT=/tmp/youtube-benchmark-$$
mkdir -p "$(dirname "$REPORT")"

router_sh() {
  sshpass -p "$PASS" ssh -T -o ConnectTimeout=25 -o StrictHostKeyChecking=no \
    root@"$ARM" \
    "sshpass -p '$PASS' ssh -T -o ConnectTimeout=20 -o StrictHostKeyChecking=no -p $ROUTER_PORT root@$ROUTER '$1'"
}

log() { echo "$*" | tee -a "$REPORT"; }

log "=== YOUTUBE BENCHMARK $(date -Is) ==="

log ""
log "--- VPS WAN (xray :8443) ---"
if sh "$ROOT/vps-youtube-test.sh" >>"$REPORT" 2>&1; then
  log "VPS_WAN=OK"
else
  log "VPS_WAN=FAIL"
fi
fin=$(ss -tn state fin-wait state fin-wait-1 state fin-wait-2 2>/dev/null | grep -c ':8443' || true)
log "VPS_FIN_WAIT_8443=$fin"

log ""
log "--- Router baseline ---"
router_sh 'export PATH=/opt/bin:/opt/sbin:$PATH
echo arch=$(uname -m)
echo nfqws2=$(pgrep nfqws2 || echo OFF)
echo skeen=$(pgrep skeen-box || echo OFF)
echo xray=$(pgrep xray || echo OFF)
echo nfqueue=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)
echo quic_drop=$(iptables-save 2>/dev/null | grep -c "udp dpt:443.*DROP" || echo 0)
/opt/bin/skeen status 2>/dev/null | head -4 || true' >>"$REPORT" 2>&1 || log "ROUTER_BASELINE=FAIL"

benchmark_strategy() {
  name="$1"
  script="$2"
  log ""
  log "--- Strategy: $name ---"
  out=$(router_sh "curl -fsSL $BASE/$script | sh" 2>&1) || out="DEPLOY_FAILED"
  echo "$out" | tail -20 >>"$REPORT"
  sleep 15
  router_sh 'export PATH=/opt/bin:/opt/sbin:$PATH
err=$(grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0)
yt=$(grep -ci youtube /opt/var/log/sing-box.log 2>/dev/null || echo 0)
ok=$(grep -c "outbound connection to www.youtube.com" /opt/var/log/sing-box.log 2>/dev/null || echo 0)
nfq=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)
nfq2=$(pgrep nfqws2 || echo OFF)
sk=$(pgrep skeen-box || echo OFF)
echo strategy_metrics errors=$err youtube_log=$yt youtube_ok=$ok nfqueue=$nfq nfqws2=$nfq2 skeen=$sk
tail -5 /opt/var/log/sing-box.log 2>/dev/null || true' >>"$REPORT" 2>&1 || true
  vps_accepts=$(journalctl -u xray-8443 --no-pager -n 30 2>/dev/null | grep -c '79.139' || true)
  log "vps_router_accepts=$vps_accepts"
}

# Test SKeen stable (option 2 - current production path)
benchmark_strategy "SKeen-52-stable" "52-youtube-stable.sh"

# Stability window
log ""
log "--- Stability 60s ---"
for i in 1 2 3 4 5 6; do
  router_sh 'grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0' 2>/dev/null | while read -r e; do
    fin=$(ss -tn state fin-wait 2>/dev/null | grep -c ':8443' || true)
    log "t${i}s errors=$e fin_wait=$fin"
  done
  sleep 10
done

log ""
log "--- Final VPS WAN ---"
sh "$ROOT/vps-youtube-test.sh" >>"$REPORT" 2>&1 && log "FINAL_VPS=OK" || log "FINAL_VPS=FAIL"

log ""
log "=== REPORT: $REPORT ==="
cat "$REPORT"
