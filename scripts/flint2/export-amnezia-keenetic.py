#!/usr/bin/env python3
"""Шаблон Amnezia client.env из keenetic-export (без private key)."""
from __future__ import annotations

import json
from pathlib import Path

EXPORT = Path(__file__).resolve().parent / "keenetic-export.json"
OUT = Path(__file__).resolve().parent / "amnezia-client.env.template"

KEY = '{"show": {"interface": {}}}'


def main() -> int:
    data = json.loads(EXPORT.read_text())
    iface = data.get(KEY, {}).get("show", {}).get("interface", {}).get("Wireguard0", {})
    wg = iface.get("wireguard", {})
    asc = wg.get("asc", {})
    peer = (wg.get("peer") or [{}])[0]
    ip = iface.get("ip", {}).get("address", {})

    lines = [
        "# Скопируйте на Flint: /etc/amnezia/client.env",
        "# AWG_CLIENT_PRIVKEY — только из Amnezia app / VPS (в экспорте Keenetic нет)",
        f"AWG_ENDPOINT=193.233.232.48:39182",
        f"AWG_SERVER_PUBKEY={peer.get('key', '')}",
        "AWG_CLIENT_PRIVKEY=REPLACE_ME",
        f"AWG_CLIENT_IP={ip.get('address', '10.8.1.10')}/32",
        f"AWG_PSK={peer.get('preshared-key', '')}",
        f"AWG_MTU={iface.get('ip', {}).get('mtu', '1324')}",
        f"AWG_JC={asc.get('jc', '4')}",
        f"AWG_JMIN={asc.get('jmin', '10')}",
        f"AWG_JMAX={asc.get('jmax', '50')}",
        f"AWG_S1={asc.get('s1', '17')}",
        f"AWG_S2={asc.get('s2', '129')}",
        f"AWG_H1={asc.get('h1', '')}",
        f"AWG_H2={asc.get('h2', '')}",
        f"AWG_H3={asc.get('h3', '')}",
        f"AWG_H4={asc.get('h4', '')}",
        "AWG_KEEPALIVE=25",
        "",
        "# Keenetic endpoint был 103.31.77.69:30315 — на VPS сейчас 193.233.232.48:39182",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
