"""Тесты Garden: каталог, промо, ссылки."""

import json
from pathlib import Path

from garden_content import build_bot_promo_post, is_special_slot
from garden_links import garden_bot_link
from sales_db import init_sales_db, list_products_for_persona


def test_garden_products_seeded(tmp_path):
    db = tmp_path / "sales.db"
    init_sales_db(db)
    garden = list_products_for_persona("garden", path=db)
    stern = list_products_for_persona("stern", path=db)
    codes_g = {p["code"] for p in garden}
    codes_s = {p["code"] for p in stern}
    assert "garden_tripwire_checklist" in codes_g
    assert "tripwire_office" in codes_s
    assert not codes_g & codes_s


def test_bot_promo_post():
    topic, body = build_bot_promo_post()
    assert "bot_promo" in topic
    assert len(body) > 50


def test_special_slot():
    assert is_special_slot({"type": "bot_promo"}) == "bot_promo"


def test_garden_link(monkeypatch):
    monkeypatch.setenv("EMPIRE_GARDEN_BOT_USERNAME", "garden_shop")
    assert "t.me/garden_shop" in (garden_bot_link("weekly") or "")


def test_products_json():
    p = Path(__file__).resolve().parents[1] / "data" / "garden_products.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert len(data["products"]) >= 2
