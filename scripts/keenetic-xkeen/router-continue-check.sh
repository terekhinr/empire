#!/bin/sh
# Continue repair: check router via armbian + telnet heal
set -eu
. /root/.keenetic-admin.env
ARM=100.80.133.85
ROUTER=192.168.1.1

router_via_arm() {
  sshpass -p "$KEENETIC_ROUTER_PASS" ssh -T -o ConnectTimeout=20 -o StrictHostKeyChecking=no root@"$ARM" "$1"
}

echo "=== PORTS ==="
router_via_arm 'for p in 22 222 23; do (echo >/dev/tcp/192.168.1.1/$p) 2>/dev/null && echo OPEN $p || echo closed $p; done'

echo "=== SSH :222 ==="
router_via_arm "sshpass -p '$KEENETIC_ROUTER_PASS' ssh -T -o ConnectTimeout=12 -o StrictHostKeyChecking=no -p 222 root@$ROUTER 'export PATH=/opt/bin:/opt/sbin:\$PATH; echo SSH_OK; pgrep -a nfqws2 || echo OFF; pgrep skeen-box || echo skeen=OFF; echo nfq=\$(iptables-save 2>/dev/null|grep -c NFQUEUE); for u in https://www.youtube.com https://www.google.com/generate_204 https://ya.ru; do echo -n \"\$u \"; curl -4 -o /dev/null -s -w \"%{http_code}\" --connect-timeout 12 \"\$u\" 2>/dev/null || echo ERR; echo; done'" 2>&1 || echo SSH_FAIL

echo "=== TELNET HEAL ==="
router_via_arm "KEENETIC_ADMIN_LOGIN='$KEENETIC_ADMIN_LOGIN' KEENETIC_ADMIN_PASSWORD='$KEENETIC_ADMIN_PASSWORD' python3 -" << 'PYEOF'
import telnetlib, time, os
H='192.168.1.1'; L=os.environ['KEENETIC_ADMIN_LOGIN']; P=os.environ['KEENETIC_ADMIN_PASSWORD']
CMD='export PATH=/opt/bin:/opt/sbin:$PATH; curl -fsSL http://193.233.232.48:8787/54-emergency-restore.sh | sh'
tn=telnetlib.Telnet(H,23,timeout=25)
tn.read_until(b'Login:',15); tn.write(L.encode()+b'\n')
tn.read_until(b'Password:',15); tn.write(P.encode()+b'\n'); time.sleep(2)
tn.read_very_eager()
tn.write(b'exec sh\r\n'); time.sleep(5)
c=tn.read_very_eager().decode('utf-8','replace')
if 'system failed' in c.lower():
    print('EXEC_SH_FAIL'); print(c[-400:]); raise SystemExit(2)
tn.write(CMD.encode()+b'\r\n'); time.sleep(45)
print(tn.read_very_eager().decode('utf-8','replace')[-4000:])
tn.write(b'exit\r\n'); tn.close()
PYEOF
