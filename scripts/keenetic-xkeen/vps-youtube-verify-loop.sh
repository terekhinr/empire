#!/bin/sh
# Полный автотест: VPS WAN + router path + стабильность 2 мин.
set -eu
ROOT=/root/projects/empire/scripts/keenetic-xkeen
ARM=100.80.133.85
ROUTER=192.168.1.1
PASS=keenetic
FAIL=0

echo "=== VPS WAN test ==="
if ! sh "$ROOT/vps-youtube-test.sh"; then
  echo "VPS WAN FAIL"
  FAIL=1
fi

fin=$(ss -tn state fin-wait state fin-wait-1 state fin-wait-2 2>/dev/null | grep -c ':8443' || true)
echo "VPS FIN_WAIT_8443=$fin"

echo "=== Router deploy 52 ==="
out=$(sshpass -p "$PASS" ssh -T -o ConnectTimeout=25 root@"$ARM" \
  "sshpass -p $PASS ssh -T -p 222 root@$ROUTER 'curl -fsSL http://193.233.232.48:8787/52-youtube-stable.sh | sh'" 2>&1) || { echo "DEPLOY FAIL"; FAIL=1; out=""; }
echo "$out" | tail -15

echo "=== Stability 120s ==="
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  e=$(sshpass -p "$PASS" ssh -T -o ConnectTimeout=20 root@"$ARM" \
    "sshpass -p $PASS ssh -T -p 222 root@$ROUTER 'tail -30 /opt/var/log/sing-box.log | grep -c ERROR || echo 0'" 2>/dev/null || echo 99)
  y=$(sshpass -p "$PASS" ssh -T -o ConnectTimeout=20 root@"$ARM" \
    "sshpass -p $PASS ssh -T -p 222 root@$ROUTER 'tail -30 /opt/var/log/sing-box.log | grep -c \"www.youtube.com\" || echo 0'" 2>/dev/null || echo 0)
  a=$(journalctl -u xray-8443 --no-pager -n 5 2>/dev/null | grep -c '79.139' || true)
  echo "t${i} err=$e yt=$y vps_accepts=$a fin=$(ss -tn state fin-wait state fin-wait-1 2>/dev/null | grep -c ':8443' || true)"
  if [ "${e:-0}" -gt 12 ] 2>/dev/null; then FAIL=1; fi
  sleep 10
done

echo "=== Final VPS test ==="
if ! sh "$ROOT/vps-youtube-test.sh"; then
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "ALL OK"
else
  echo "SOME CHECKS FAILED"
fi
exit $FAIL
