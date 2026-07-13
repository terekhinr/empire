#!/usr/bin/env python3
"""С HA-хоста: telnet Keenetic exec sh → probe Flint."""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def main() -> int:
    env = os.environ.copy()
    pfile = "/root/.keenetic-admin.env"
    if os.path.isfile(pfile):
        with open(pfile, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip().strip('"'))
    login = env.get("KEENETIC_ADMIN_LOGIN", "admin")
    password = env.get("KEENETIC_ADMIN_PASSWORD", "")
    script = textwrap.dedent(
        f'''
        import telnetlib, time
        H="192.168.1.1"; L={login!r}; P={password!r}
        cmd="curl -sI -m5 http://192.168.8.1/; curl -sI -m5 http://192.168.1.99/; ping -c2 -W2 192.168.8.1; ping -c2 -W2 192.168.1.99"
        tn=telnetlib.Telnet(H,23,timeout=25)
        tn.read_until(b"Login:",15); tn.write(L.encode()+b"\\n")
        tn.read_until(b"Password:",15); tn.write(P.encode()+b"\\n"); time.sleep(2)
        tn.read_very_eager(); tn.write(b"exec sh\\r\\n"); time.sleep(4)
        tn.read_very_eager(); tn.write(cmd.encode()+b"\\r\\n"); time.sleep(12)
        print(tn.read_very_eager().decode("utf-8","replace")[-4000:])
        tn.write(b"exit\\r\\n"); tn.close()
        '''
    ).strip()
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@100.80.133.85", "python3 -"],
        input=script.encode(),
        env=env,
        capture_output=True,
        timeout=60,
    )
    sys.stdout.buffer.write(p.stdout)
    sys.stderr.buffer.write(p.stderr)
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
