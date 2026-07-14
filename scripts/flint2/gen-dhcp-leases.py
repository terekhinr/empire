#!/usr/bin/env python3
"""Генерация DHCP static leases для OpenWrt из keenetic-export.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPORT = Path(__file__).resolve().parent / "keenetic-export.json"
OUT = Path(__file__).resolve().parent / "dhcp-static-leases.sh"

# Приоритетные устройства (имя → сохранить IP)
PRIORITY = {
    "a8:21:08:f0:34:d7": "Home Assistant",
    "bc:fa:b8:be:18:7b": "camera_max_room",
    "bc:fa:b8:c5:e7:90": "camera_kitchen",  # may differ
    "94:de:80:64:ed:e6": "Destroy_PC",
    "8c:4b:14:ea:e1:28": "SmartIntercom",
    "e8:f4:94:fe:6d:36": "ezviz_podezd",
}


def main() -> int:
    data = json.loads(EXPORT.read_text())
    hosts = []
    for val in data.values():
        walk(val, hosts)

    lines = [
        "#!/bin/sh",
        "# Static DHCP leases migrated from Keenetic",
        "set -eu",
    ]
    seen = set()
    for h in sorted(hosts, key=lambda x: str(x.get("ip", ""))):
        mac = h.get("mac") or ""
        ip = h.get("ip") or ""
        name = (h.get("hostname") or h.get("name") or mac).split(" - ")[0]
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:32]
        if not mac or not ip or ip.startswith("0."):
            continue
        if mac in seen:
            continue
        seen.add(mac)
        lines.append(f"uci add dhcp host 2>/dev/null || true")
        lines.append(f"uci set dhcp.@host[-1].mac='{mac}'")
        lines.append(f"uci set dhcp.@host[-1].ip='{ip}'")
        lines.append(f"uci set dhcp.@host[-1].name='{name}'")
        lines.append("")
    lines.append("uci commit dhcp")
    lines.append("/etc/init.d/dnsmasq restart")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {len(seen)} leases → {OUT}")
    return 0


def norm_mac(val) -> str:
    if isinstance(val, str):
        return val.lower()
    return ""


def norm_ip(val) -> str:
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        addr = val.get("address")
        if isinstance(addr, dict):
            return str(addr.get("address", ""))
        if isinstance(addr, str):
            return addr
    return ""


def walk(obj, out: list) -> None:
    if isinstance(obj, dict):
        mac = norm_mac(obj.get("mac"))
        ip = norm_ip(obj.get("ip"))
        if mac and ip and not ip.startswith("0."):
            out.append({"mac": mac, "ip": ip, "hostname": obj.get("hostname") or obj.get("name") or ""})
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for i in obj:
            walk(i, out)


if __name__ == "__main__":
    raise SystemExit(main())
