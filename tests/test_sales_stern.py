from pathlib import Path

from sales_db import init_sales_db, list_products, npd_limit_alert


def test_products_seed(tmp_path):
    db = tmp_path / "sales.db"
    init_sales_db(db)
    prods = list_products(path=db)
    codes = {p["code"] for p in prods}
    assert "tripwire_office" in codes
    assert prods[0]["payments_enabled"] == 0


def test_npd_alert(tmp_path):
    db = tmp_path / "sales.db"
    init_sales_db(db)
    a = npd_limit_alert(db)
    assert "pct" in a
