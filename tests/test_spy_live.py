"""Маршрутизация spy: live vs dry-run."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import spy_config


def test_run_spy_collect_uses_live_when_session_ready(monkeypatch):
    import telethon_spy as ts

    monkeypatch.setattr(spy_config, "spy_live_enabled", lambda: True)
    live = AsyncMock(return_value={"inserted": 2, "skipped": 1})
    dry = AsyncMock(return_value={"inserted": 0, "disabled": "dry_run_off"})
    monkeypatch.setattr(ts, "run_spy_live", live)
    monkeypatch.setattr(ts, "run_spy_dry_run", dry)

    session = MagicMock()
    out = asyncio.run(ts.run_spy_collect(session))
    assert out["inserted"] == 2
    live.assert_awaited_once()
    dry.assert_not_awaited()
