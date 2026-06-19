#!/usr/bin/env python3
"""Generate XKeen 04_outbounds.json from vless:// link (3X-UI / Reality)."""
from __future__ import annotations

import json
import sys
from urllib.parse import parse_qs, urlparse


def parse_vless(url: str) -> dict:
    url = url.strip()
    if not url.startswith("vless://"):
        raise SystemExit("URL must start with vless://")

    parsed = urlparse(url)
    if not parsed.hostname or not parsed.username:
        raise SystemExit("Invalid vless URL: missing uuid or host")

    q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    port = parsed.port or 443

    return {
        "uuid": parsed.username,
        "address": parsed.hostname,
        "port": port,
        "publicKey": q.get("pbk", ""),
        "fingerprint": q.get("fp", "chrome"),
        "serverName": q.get("sni", ""),
        "shortId": q.get("sid", ""),
        "flow": q.get("flow", "xtls-rprx-vision"),
    }


def build_outbounds(v: dict) -> dict:
    return {
        "outbounds": [
            {
                "tag": "vless-reality",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": v["address"],
                            "port": v["port"],
                            "users": [
                                {
                                    "id": v["uuid"],
                                    "flow": v["flow"],
                                    "encryption": "none",
                                    "level": 0,
                                }
                            ],
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "publicKey": v["publicKey"],
                        "fingerprint": v["fingerprint"],
                        "serverName": v["serverName"],
                        "shortId": v["shortId"],
                        "spiderX": "/",
                    },
                },
            },
            {"protocol": "freedom", "tag": "direct"},
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {"response": {"type": "http"}},
            },
        ]
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: vless_to_outbound.py 'vless://...' [output.json]", file=sys.stderr)
        raise SystemExit(1)

    v = parse_vless(sys.argv[1])
    for key in ("publicKey", "serverName", "shortId"):
        if not v[key]:
            print(f"Warning: missing {key} in vless URL", file=sys.stderr)

    out = json.dumps(build_outbounds(v), indent=4, ensure_ascii=False)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Written: {sys.argv[2]}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
