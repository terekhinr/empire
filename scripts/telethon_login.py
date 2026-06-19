#!/usr/bin/env python3
"""Однократный вход Telethon → файл empire_spy.session в корне проекта."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

API_ID = os.getenv("TELETHON_API_ID", "").strip()
API_HASH = os.getenv("TELETHON_API_HASH", "").strip()
SESSION = os.getenv("TELETHON_SESSION", str(ROOT / "empire_spy"))


async def main() -> None:
    if not API_ID or not API_HASH:
        print("Задайте TELETHON_API_ID и TELETHON_API_HASH в .env", file=sys.stderr)
        sys.exit(1)
    from telethon import TelegramClient

    client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"OK: сессия {SESSION}.session, user={me.username or me.id}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
