"""GPB HTML importer maps ISIN → MOEX ticker."""

from __future__ import annotations

from pathlib import Path

from portfolio import db as pdb
from portfolio.importers.gpb_html import import_gpb_html


def test_gpb_maps_isin(tmp_db, tmp_path: Path, monkeypatch):
    html = tmp_path / "brok_rpt_bo_20260101_20260801_x.html"
    html.write_text(
        """
        <html><body>
        <table>
        <tr><td>Наименование ЦБ</td><td>x</td><td>y</td><td>ISIN</td></tr>
        <tr>
          <td>1</td><td>Сбербанк ао</td><td></td><td>RU0009029540</td>
          <td></td><td></td><td></td>
          <td>10</td><td></td><td></td><td></td>
          <td>270,50</td><td>0</td>
        </tr>
        </table>
        </body></html>
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "portfolio.importers.gpb_html.isin_to_ticker",
        lambda isin: "SBER" if isin == "RU0009029540" else None,
    )
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        res = import_gpb_html(conn, html)
        assert res["positions_updated"] == 1
        row = conn.execute(
            """
            SELECT i.ticker, mp.quantity, mp.avg_price
            FROM manual_positions mp
            JOIN instruments i ON i.id = mp.instrument_id
            """
        ).fetchone()
    assert row["ticker"] == "SBER"
    assert abs(row["quantity"] - 10) < 0.01
    assert abs(row["avg_price"] - 270.5) < 0.01
