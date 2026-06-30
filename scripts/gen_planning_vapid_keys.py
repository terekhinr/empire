#!/usr/bin/env python3
"""Generate VAPID key pair for Empire Tasks Web Push.

Usage:
  ./venv/bin/python scripts/gen_planning_vapid_keys.py
  ./venv/bin/python scripts/gen_planning_vapid_keys.py --write-env

Writes PLANNING_VAPID_* to .env when --write-env (skips if already set).
"""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def generate_vapid_keys() -> tuple[str, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public_bytes).decode().rstrip("=")
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return public_b64, private_pem


def write_env(public_b64: str, private_pem: str) -> bool:
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.is_file() else ""
    if re.search(r"^PLANNING_VAPID_PUBLIC_KEY=", text, re.M):
        print("PLANNING_VAPID_* already in .env — skipped")
        return False
    block = (
        "\n# Empire Tasks Web Push (VAPID)\n"
        f'PLANNING_VAPID_PUBLIC_KEY="{public_b64}"\n'
        f'PLANNING_VAPID_PRIVATE_KEY="{private_pem.replace(chr(10), "\\n")}"\n'
        'PLANNING_VAPID_CONTACT="mailto:info@neverretire.ru"\n'
    )
    ENV_PATH.write_text(text.rstrip() + block, encoding="utf-8")
    print(f"Wrote VAPID keys to {ENV_PATH}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-env", action="store_true")
    args = parser.parse_args()
    public_b64, private_pem = generate_vapid_keys()
    if args.write_env:
        write_env(public_b64, private_pem)
    else:
        print("Public key (for browser subscribe):")
        print(public_b64)
        print("Run with --write-env to append keys to .env")


if __name__ == "__main__":
    main()
