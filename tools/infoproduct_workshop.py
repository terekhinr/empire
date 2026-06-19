#!/usr/bin/env python3
"""
Симуляция диалога «покупатель ↔ продавец» для инфопродукта (один проход LLM API).

Пример:
  ./venv/bin/python tools/infoproduct_workshop.py --persona garden --product garden_tripwire_checklist
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    env_path = REPO / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def _load_product(persona: str, code: str) -> dict:
    if persona == "garden":
        data = json.loads((REPO / "data" / "garden_products.json").read_text(encoding="utf-8"))
    elif persona == "stern":
        data = json.loads((REPO / "data" / "stern_products.json").read_text(encoding="utf-8"))
    else:
        raise SystemExit(f"unknown persona: {persona}")
    for p in data.get("products", []):
        if p.get("code") == code:
            return p
    raise SystemExit(f"product not found: {code}")


def _positioning(persona: str) -> str:
    if persona == "garden":
        path = REPO / "docs" / "garden_positioning.md"
    else:
        path = REPO / "docs" / "tz bot zhelenaya spina.txt"
    if not path.is_file():
        return ""
    raw = path.read_bytes()
    for enc in ("utf-8", "cp1251"):
        try:
            return raw.decode(enc)[:6000]
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")[:6000]


async def run_dialogue(persona: str, product: dict) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "Нет OPENROUTER_API_KEY / DEEPSEEK_API_KEY — заполните .env и повторите."

    pos = _positioning(persona)
    buyer = (
        "Ты — скептичный покупатель из ЦФО. Задаёшь 6 коротких вопросов подряд "
        f"о продукте «{product['name']}» за {product['price_rub']} ₽. "
        "Боишься воды, шаблонов и пустых обещаний. Пиши по-русски, по одному вопросу за раз."
    )
    persona_rules = {
        "garden": "Не обещай гарантированный урожай. Средняя полоса, полевые тесты.",
        "stern": (
            "Продукт про спину, офис, гирю, McGill-логику. НЕ про историю гиревого спорта. "
            "Дисклеймер: не замена врачу. Не обещай исцеление."
        ),
    }
    seller = (
        "Ты — продавец канала (не агрессивный). Отвечаешь только правдой из карточки продукта "
        f"и ТЗ. {persona_rules.get(persona, '')} "
        f"Продукт: {json.dumps(product, ensure_ascii=False)}\n\nКОНТЕКСТ:\n{pos}"
    )
    prompt = (
        f"{buyer}\n\n{seller}\n\n"
        "Сформируй диалог из 6 пар вопрос–ответ, затем блок «ВЫВОД ДЛЯ РЕДАКТОРА»: "
        "3 сильные стороны оффера, 3 слабых, 3 правки в PDF/лендинге."
    )
    url = os.environ.get("OPENROUTER_BASE", "https://openrouter.ai/api/v1/chat/completions")
    model = os.environ.get("WORKSHOP_MODEL", "deepseek/deepseek-chat")
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def main() -> None:
    _load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True, choices=("garden", "stern"))
    ap.add_argument("--product", required=True)
    args = ap.parse_args()
    product = _load_product(args.persona, args.product)
    import asyncio

    text = asyncio.run(run_dialogue(args.persona, product))
    out = REPO / "data" / f"infoproduct_workshop_{args.persona}_{args.product}.md"
    out.write_text(
        f"# Workshop {args.persona} / {args.product}\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"OK → {out}")


if __name__ == "__main__":
    main()
