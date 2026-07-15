#!/usr/bin/env python3
"""Amnezia .vpn → /etc/amnezia/client.env + awg0.conf (для Flint)."""
from __future__ import annotations

import base64
import json
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_IN = Path("/root/projects/empire/data/amnezia_config.vpn")
OUT_ENV = ROOT / "amnezia-client.env"
OUT_CONF = ROOT / "amnezia-awg0.conf"


def decode_vpn(text: str) -> dict:
    text = text.strip()
    if text.startswith("vpn://"):
        text = text[6:]
    if not text.endswith("=="):
        text += "=="
    raw = base64.urlsafe_b64decode(text)
    # Amnezia: 4-byte zlib header then deflate
    if raw[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
        payload = zlib.decompress(raw)
    else:
        payload = zlib.decompress(raw[4:])
    return json.loads(payload)


def wg_kv(conf: str) -> dict[str, str]:
    out: dict[str, str] = {}
    section = ""
    for line in conf.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[f"{section}.{k.strip()}"] = v.strip()
    return out


def pick_container(data: dict) -> tuple[str, dict]:
    for c in data.get("containers", []):
        name = (c.get("container") or "").lower()
        if c.get("awg"):
            return name or "awg", c["awg"]
        if c.get("wireguard"):
            return name or "wireguard", c["wireguard"]
        if name in ("amnezia-awg", "awg", "wireguard"):
            inner = c.get(name) or c.get("awg") or c.get("wireguard") or {}
            return name, inner
    raise SystemExit("AWG container not found in .vpn")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    if not src.is_file():
        print(f"Нет файла: {src}", file=sys.stderr)
        print("Положите amnezia_config.vpn в data/ на VPS", file=sys.stderr)
        return 1

    raw = src.read_text(encoding="utf-8", errors="replace").strip()
    data = decode_vpn(raw)
    _, container = pick_container(data)
    last = json.loads(container["last_config"])
    conf = last["config"]
    conf = conf.replace("$PRIMARY_DNS", data.get("dns1", "1.1.1.1"))
    conf = conf.replace("$SECONDARY_DNS", data.get("dns2", "1.0.0.1"))

    kv = wg_kv(conf)
    endpoint = kv.get("[Peer].Endpoint", "")
    if not endpoint and data.get("hostName"):
        port = container.get("port") or data.get("port") or 39182
        endpoint = f"{data['hostName']}:{port}"

    env_lines = [
        "# auto from amnezia_config.vpn — не коммитить",
        f"AWG_ENDPOINT={endpoint}",
        f"AWG_SERVER_PUBKEY={kv.get('[Peer].PublicKey', '')}",
        f"AWG_CLIENT_PRIVKEY={kv.get('[Interface].PrivateKey', '')}",
        f"AWG_CLIENT_IP={kv.get('[Interface].Address', '10.8.1.10/32')}",
        f"AWG_PSK={kv.get('[Peer].PresharedKey', kv.get('[Peer].PreSharedKey', ''))}",
        f"AWG_MTU={kv.get('[Interface].MTU', '1324')}",
        f"AWG_JC={kv.get('[Interface].Jc', '4')}",
        f"AWG_JMIN={kv.get('[Interface].Jmin', '10')}",
        f"AWG_JMAX={kv.get('[Interface].Jmax', '50')}",
        f"AWG_S1={kv.get('[Interface].S1', '17')}",
        f"AWG_S2={kv.get('[Interface].S2', '129')}",
        f"AWG_H1={kv.get('[Interface].H1', '')}",
        f"AWG_H2={kv.get('[Interface].H2', '')}",
        f"AWG_H3={kv.get('[Interface].H3', '')}",
        f"AWG_H4={kv.get('[Interface].H4', '')}",
        f"AWG_KEEPALIVE={kv.get('[Peer].PersistentKeepalive', '25')}",
    ]
    OUT_ENV.write_text("\n".join(env_lines) + "\n")
    OUT_CONF.write_text(conf + "\n")
    print(f"Wrote {OUT_ENV}")
    print(f"Wrote {OUT_CONF}")
    print(f"Endpoint: {endpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
