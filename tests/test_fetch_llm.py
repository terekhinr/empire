"""Retry и безопасный разбор ответа OpenRouter."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


def test_fetch_llm_retries_on_invalid_json():
    import main

    bad = MagicMock()
    bad.status_code = 200
    bad.text = "<html>502 Bad Gateway</html>\n" * 20

    good = MagicMock()
    good.status_code = 200
    good.text = json.dumps(
        {"choices": [{"message": {"content": "ТЕКСТ:\nПривет\n\nПРОМПТ:\nx"}}]}
    )

    client = AsyncMock()
    client.post = AsyncMock(side_effect=[bad, good])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    async def _run():
        with patch("main.httpx.AsyncClient", return_value=client), patch(
            "main.asyncio.sleep", new_callable=AsyncMock
        ):
            return await main.fetch_llm_response(
                "deepseek/deepseek-chat", "hi", max_attempts=2
            )

    status, data = asyncio.run(_run())
    assert status == 200
    assert "choices" in data
    assert client.post.await_count == 2
