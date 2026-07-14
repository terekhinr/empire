#!/usr/bin/env python3
"""Сборка keenetic-snapshot.json + скриптов восстановления из keenetic-export.json."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORT = ROOT / "keenetic-export.json"
SNAPSHOT = ROOT / "keenetic-snapshot.json"
ENV_OUT = ROOT / "keenetic-restore.env"
DHCP_SH = ROOT / "dhcp-static-leases.sh"
WIFI_PSK = ROOT / "wifi-psk.txt"


def load_export() -> dict:
    return json.loads(EXPORT.read_text())


def walk(obj, fn) -> None:
    if isinstance(obj, dict):
        fn(obj)
        for v in obj.values():
            walk(v, fn)
    elif isinstance(obj, list):
        for i in obj:
            walk(i, fn)


def find_wifi(data: dict) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def grab(d: dict) -> None:
        ssid = d.get("ssid")
        sec = d.get("security") or {}
        psk = None
        if isinstance(sec, dict):
            psk = (sec.get("wpa-psk") or {}).get("psk")
        if ssid and psk and ssid not in seen:
            seen.add(ssid)
            out.append(
                {
                    "ssid": ssid,
                    "psk": psk,
                    "encryption": "psk2" if sec.get("wpa2") else "psk",
                }
            )

    walk(data, grab)
    return out


def find_dhcp_pool(data: dict) -> dict:
    pool = {"start": "33", "limit": "120", "leasetime": "7h"}

    def grab(d: dict) -> None:
        r = d.get("range")
        if not isinstance(r, dict):
            return
        begin = str(r.get("begin", ""))
        if not begin.startswith("192.168.1."):
            return
        pool["start"] = str(int(begin.split(".")[-1]))
        pool["limit"] = str(r.get("size", 120))
        lease = int(d.get("lease", 25200))
        pool["leasetime"] = f"{max(1, lease // 3600)}h"

    for val in data.values():
        walk(val, grab)
    return pool


def find_lan(data: dict) -> dict:
    lan = {"ip": "192.168.1.1", "mask": "255.255.255.0", "hostname": "flint2"}

    def grab_addr(d: dict) -> None:
        addr = d.get("address")
        if not isinstance(addr, dict):
            return
        ip = addr.get("address", "")
        if ip.startswith("192.168.1.") and addr.get("mask") == "255.255.255.0":
            lan["ip"] = ip
            lan["mask"] = addr.get("mask", "255.255.255.0")

    def grab_host(d: dict) -> None:
        if d.get("hostname") == "Keenetic_Giga":
            lan["keenetic_hostname"] = "Keenetic_Giga"

    for val in data.values():
        walk(val, grab_addr)
        walk(val, grab_host)
    return lan


def find_dns(data: dict) -> list[str]:
    dns: list[str] = []

    def grab(d: dict) -> None:
        addr = d.get("address")
        if isinstance(addr, str) and re.match(r"^\d+\.\d+\.\d+\.\d+$", addr) and addr not in dns:
            dns.append(addr)

    for val in data.values():
        walk(val, grab)
    return dns[:4] or ["1.1.1.1", "1.0.0.1"]


def norm_mac(v) -> str:
    return str(v or "").lower()


def norm_ip(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        a = v.get("address")
        if isinstance(a, dict):
            return str(a.get("address", ""))
        if isinstance(a, str):
            return a
    return ""


def find_static_hosts(data: dict) -> list[dict]:
    hosts: dict[str, dict] = {}

    def add(mac, ip, name="", registered=False) -> None:
        mac = norm_mac(mac)
        ip = norm_ip(ip) if not isinstance(ip, str) else ip
        if not mac or not ip or not ip.startswith("192.168.1."):
            return
        if ip in ("192.168.1.1", "192.168.1.0", "192.168.1.255"):
            return
        cur = hosts.get(mac, {})
        if registered or not cur:
            hosts[mac] = {
                "mac": mac,
                "ip": ip,
                "name": (name or cur.get("name") or mac.replace(":", "_"))[:48],
                "registered": registered or cur.get("registered", False),
            }

    def grab_host(d: dict) -> None:
        if not d.get("mac") or not d.get("ip"):
            return
        add(
            d.get("mac"),
            d.get("ip"),
            d.get("hostname") or d.get("name") or "",
            bool(d.get("registered")),
        )

    def grab_static(d: dict) -> None:
        if d.get("mac") and d.get("ip") and isinstance(d.get("ip"), str):
            mac = norm_mac(d.get("mac"))
            if mac in hosts and hosts[mac].get("name") not in ("", "static"):
                return
            add(d.get("mac"), d.get("ip"), d.get("name") or "static", True)

    for val in data.values():
        walk(val, grab_host)
        walk(val, grab_static)

    return sorted(hosts.values(), key=lambda h: h["ip"])


def sanitize_name(name: str) -> str:
    base = name.split(" - ")[0].strip()
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in base)[:32] or "host"


def write_dhcp_sh(hosts: list[dict]) -> None:
    lines = [
        "#!/bin/sh",
        "# Static DHCP — автоген из keenetic-export.json",
        "set -eu",
        "# очистка старых host-секций (OpenWrt)",
        "while uci -q delete dhcp.@host[0]; do :; done",
        "",
    ]
    for h in hosts:
        name = sanitize_name(h["name"])
        lines += [
            "uci add dhcp host 2>/dev/null || true",
            f"uci set dhcp.@host[-1].mac='{h['mac']}'",
            f"uci set dhcp.@host[-1].ip='{h['ip']}'",
            f"uci set dhcp.@host[-1].name='{name}'",
            "",
        ]
    lines += ["uci commit dhcp", "/etc/init.d/dnsmasq restart"]
    DHCP_SH.write_text("\n".join(lines) + "\n")


def write_env(snapshot: dict) -> None:
    w = snapshot["wifi"]["primary"]
    pool = snapshot["dhcp"]["pool"]
    lines = [
        f"# keenetic-restore.env — {snapshot['meta']['exported_at']}",
        f"KEENETIC_WIFI_SSID={w['ssid']}",
        f"KEENETIC_WIFI_PSK={w['psk']}",
        f"KEENETIC_LAN_IP={snapshot['lan']['ip']}",
        f"KEENETIC_LAN_MASK={snapshot['lan']['mask']}",
        f"KEENETIC_DHCP_START={pool['start']}",
        f"KEENETIC_DHCP_LIMIT={pool['limit']}",
        f"KEENETIC_DHCP_LEASE={pool['leasetime']}",
        f"KEENETIC_DNS={','.join(snapshot['dns'])}",
        f"KEENETIC_TIMEZONE={snapshot['system']['timezone']}",
        f"TRANSMISSION_DOWNLOAD={snapshot['transmission']['download_dir']}",
        f"TRANSMISSION_WINDOW={snapshot['transmission']['window']}",
    ]
    ENV_OUT.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not EXPORT.is_file():
        raise SystemExit(f"Нет {EXPORT} — сначала: python3 export-keenetic.py")

    data = load_export()
    wifi_list = find_wifi(data)
    primary = next((w for w in wifi_list if w["ssid"] == "Destroy"), wifi_list[0] if wifi_list else {"ssid": "Destroy", "psk": "", "encryption": "psk2"})
    hosts = find_static_hosts(data)

    snapshot = {
        "meta": {
            "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": str(EXPORT.name),
            "hosts_count": len(hosts),
        },
        "lan": find_lan(data),
        "dhcp": {"pool": find_dhcp_pool(data), "static_hosts": hosts},
        "wifi": {"primary": primary, "all": wifi_list},
        "dns": find_dns(data),
        "system": {"timezone": "Europe/Moscow", "domain": "HOME"},
        "transmission": {
            "download_dir": "/mnt/usb/downloads",
            "window": "01:00-05:59",
            "timezone": "Europe/Moscow",
            "note": "Keenetic встроенный transmission; на Flint — 06-transmission.sh",
        },
        "guest_network": {"ip": "10.1.30.1", "mask": "255.255.255.0", "note": "Guest Wi-Fi на Keenetic — на Flint не мигрируем автоматически"},
        "important_hosts": {
            "home_assistant": next((h for h in hosts if h["ip"] == "192.168.1.41"), None),
            "destroy_pc": next((h for h in hosts if h["ip"] == "192.168.1.112"), None),
        },
    }

    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    write_dhcp_sh(hosts)
    if primary.get("psk"):
        WIFI_PSK.write_text(primary["psk"] + "\n")
    write_env(snapshot)

    print(f"Wrote {SNAPSHOT} ({len(hosts)} static hosts)")
    print(f"Wrote {ENV_OUT}, {DHCP_SH}, {WIFI_PSK.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
