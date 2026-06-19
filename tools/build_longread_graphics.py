#!/usr/bin/env python3
"""SVG-инфографика для лонгридов pension 01–02 (Дзен/VK)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT01 = ROOT / "data/pension/longreads/graphics/01"
OUT02 = ROOT / "data/pension/longreads/graphics/02"

STYLE = """
  <style>
    text { font-family: 'DejaVu Sans', Arial, sans-serif; fill: #1a1a2e; }
    .title { font-size: 22px; font-weight: bold; }
    .sub { font-size: 13px; fill: #555; }
    .axis { stroke: #ccc; stroke-width: 1; }
    .grid { stroke: #eee; stroke-width: 1; }
    .accent { fill: #e85d04; }
    .blue { fill: #2563eb; }
    .green { fill: #16a34a; }
    .red { fill: #dc2626; }
    .line-kids { stroke: #2563eb; stroke-width: 3; fill: none; }
    .line-workers { stroke: #16a34a; stroke-width: 3; fill: none; }
    .line-old { stroke: #e85d04; stroke-width: 3; fill: none; }
    .bar { fill: #2563eb; }
    .bar-hi { fill: #e85d04; }
    .ref { stroke: #dc2626; stroke-width: 2; stroke-dasharray: 6 4; }
  </style>
"""


def wrap(path: Path, body: str, w: int = 960, h: int = 540) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
{STYLE}
{body}
</svg>"""
    path.write_text(svg, encoding="utf-8")


def demography_lines() -> None:
    body = """
  <text x="40" y="36" class="title">Демография на 100 человек: 1900 → 2100</text>
  <text x="40" y="58" class="sub">Дети падают, старики растут · вертикаль 2033 — «минимум нагрузки» (РФ)</text>
  <line x1="80" y1="420" x2="900" y2="420" class="axis"/>
  <line x1="80" y1="90" x2="80" y2="420" class="axis"/>
  <text x="120" y="450" class="sub">1900</text>
  <text x="340" y="450" class="sub">2000</text>
  <text x="520" y="450" class="sub">2033</text>
  <text x="700" y="450" class="sub">2050</text>
  <text x="860" y="450" class="sub">2100</text>
  <line x1="520" y1="90" x2="520" y2="420" class="ref"/>
  <text x="530" y="110" class="sub" fill="#dc2626">2033</text>
  <polyline class="line-kids" points="80,120 200,150 340,200 520,280 700,340 900,380"/>
  <polyline class="line-workers" points="80,300 200,260 340,200 520,220 700,260 900,300"/>
  <polyline class="line-old" points="80,380 200,360 340,320 520,300 700,260 900,200"/>
  <rect x="620" y="100" width="14" height="14" class="blue"/><text x="642" y="112" class="sub">Дети</text>
  <rect x="620" y="122" width="14" height="14" class="green"/><text x="642" y="134" class="sub">Работающие</text>
  <rect x="620" y="144" width="14" height="14" class="accent"/><text x="642" y="156" class="sub">Старики 65+</text>
"""
    wrap(OUT01 / "01_demography_lines.svg", body)


def tfr_countries() -> None:
    rows = [("Индия", 1.9, 380), ("Бразилия", 1.6, 320), ("Китай", 1.0, 200), ("Юж. Корея", 0.8, 160)]
    bars = ""
    y = 120
    for name, val, w in rows:
        bars += f'<text x="40" y="{y+18}" class="sub">{name}</text>\n'
        bars += f'<rect x="160" y="{y}" width="{w}" height="28" class="bar"/>\n'
        bars += f'<text x="{170+w}" y="{y+20}" class="sub">{val}</text>\n'
        y += 48
    body = f"""
  <text x="40" y="36" class="title">СКР по странам vs порог замещения 2,1</text>
  <text x="40" y="58" class="sub">Суммарный коэффициент рождаемости (детей на женщину)</text>
  <line x1="160" y1="90" x2="160" y2="340" class="axis"/>
  <line x1="422" y1="90" x2="422" y2="340" class="ref"/>
  <text x="428" y="105" class="sub" fill="#dc2626">2,1 — замещение</text>
  {bars}
"""
    wrap(OUT01 / "02_tfr_countries.svg", body)


def korea_wave() -> None:
    body = """
  <text x="40" y="36" class="title">Южная Корея: «рекорд» без победы</text>
  <text x="40" y="58" class="sub">СКР 0,80 при норме 2,1 · всплеск = последнее многочисленное поколение</text>
  <line x1="80" y1="380" x2="880" y2="380" class="axis"/>
  <rect x="120" y="300" width="60" height="80" class="bar"/>
  <rect x="220" y="310" width="60" height="70" class="bar"/>
  <rect x="320" y="290" width="60" height="90" class="bar"/>
  <rect x="420" y="200" width="80" height="180" class="bar-hi"/>
  <rect x="540" y="320" width="60" height="60" class="bar"/>
  <rect x="640" y="340" width="60" height="40" class="bar"/>
  <text x="430" y="190" class="sub" fill="#e85d04">2025</text>
  <text x="650" y="330" class="sub">2027↓</text>
  <text x="120" y="400" class="sub">2020</text>
  <text x="420" y="400" class="sub">2025</text>
  <text x="640" y="400" class="sub">2027</text>
  <line x1="160" y1="120" x2="840" y2="120" class="ref"/>
  <text x="160" y="110" class="sub" fill="#dc2626">Норма 2,1</text>
"""
    wrap(OUT01 / "03_korea_wave.svg", body)


def africa_tfr() -> None:
    body = """
  <text x="40" y="36" class="title">Африка: рождаемость падает быстрее мифа</text>
  <text x="40" y="58" class="sub">СКР: ~6,8 (1970-е) → ~4,0 сегодня (−40% за полвека)</text>
  <line x1="100" y1="380" x2="860" y2="380" class="axis"/>
  <line x1="100" y1="100" x2="100" y2="380" class="axis"/>
  <polyline class="line-old" points="100,120 250,160 400,210 550,270 700,310 860,340"/>
  <circle cx="100" cy="120" r="6" class="accent"/>
  <text x="110" y="115" class="sub">6,8</text>
  <circle cx="860" cy="340" r="6" class="accent"/>
  <text x="800" y="335" class="sub">4,0</text>
  <text x="120" y="400" class="sub">1970</text>
  <text x="820" y="400" class="sub">2025</text>
"""
    wrap(OUT01 / "04_africa_tfr.svg", body)


def pension_formula() -> None:
    body = """
  <text x="40" y="40" class="title">Страховая пенсия (с 01.01.2026)</text>
  <text x="40" y="120" class="title" fill="#2563eb">Пенсия = ИПК × 156,76 ₽ + 9 584,69 ₽</text>
  <text x="40" y="170" class="sub">ИПК — индивидуальный пенсионный коэффициент (баллы, не рубли)</text>
  <text x="40" y="200" class="sub">156,76 ₽ — стоимость балла (решает бюджет)</text>
  <text x="40" y="230" class="sub">9 584,69 ₽ — фиксированная выплата (ФВ)</text>
  <text x="40" y="300" class="sub">Минимум: 30 баллов × 15 лет стажа ≈ 14 287 ₽/мес</text>
  <text x="40" y="360" class="sub">Зарплата → баллы → бюджет назначает рубль → пенсия</text>
"""
    wrap(OUT02 / "01_pension_formula.svg", body, h=420)


def ball_cost() -> None:
    pts = [(2019, 87.24, 80), (2022, 118.10, 280), (2024, 133.05, 440), (2025, 145.69, 560), (2026, 156.76, 700)]
    circles = ""
    labels = ""
    for year, val, x in pts:
        y = 380 - (val - 80) * 2.2
        circles += f'<circle cx="{x}" cy="{y:.0f}" r="7" class="accent"/>\n'
        labels += f'<text x="{x-18}" y="410" class="sub">{year}</text>\n'
        labels += f'<text x="{x-22}" y="{y-12:.0f}" class="sub">{val:.0f}</text>\n'
    body = f"""
  <text x="40" y="36" class="title">Стоимость пенсионного балла: 2019–2026</text>
  <text x="40" y="58" class="sub">Решение бюджета, не доходность «вашего счёта»</text>
  <line x1="60" y1="380" x2="760" y2="380" class="axis"/>
  <polyline class="line-old" points="80,188 280,96 440,163 560,235 700,211"/>
  {circles}
  {labels}
"""
    wrap(OUT02 / "02_ball_cost.svg", body)


def moratorium() -> None:
    body = """
  <text x="40" y="36" class="title">Накопительная часть: мораторий с 2014</text>
  <rect x="60" y="100" width="140" height="50" rx="8" fill="#dbeafe"/>
  <text x="80" y="132" class="sub">6% взносов</text>
  <text x="240" y="132" class="sub">→</text>
  <rect x="270" y="90" width="180" height="70" rx="8" fill="#fecaca"/>
  <text x="290" y="120" class="sub">🔒 Мораторий</text>
  <text x="290" y="142" class="sub">с 2014, продлевают</text>
  <text x="470" y="132" class="sub">→</text>
  <rect x="500" y="100" width="200" height="50" rx="8" fill="#fed7aa"/>
  <text x="520" y="132" class="sub">Общий котёл</text>
  <text x="60" y="220" class="sub">Текущим пенсионерам</text>
  <rect x="60" y="250" width="200" height="50" rx="8" fill="#bbf7d0"/>
  <text x="80" y="282" class="sub">ПДС — добровольно</text>
  <text x="280" y="282" class="sub">(ваш отдельный выбор)</text>
"""
    wrap(OUT02 / "03_moratorium.svg", body, h=360)


def world_reforms() -> None:
    items = [
        (80, 120, "Швеция", "«тормоз» при дефиците"),
        (320, 120, "Греция", "срез 10%+"),
        (560, 120, "Франция", "возраст 64"),
        (80, 260, "Великобритания", "льгота на отопление"),
        (320, 260, "США", "Social Security"),
        (560, 260, "Чили", "частные AFP"),
    ]
    boxes = ""
    for x, y, country, note in items:
        boxes += f'<rect x="{x}" y="{y}" width="200" height="90" rx="8" fill="#f1f5f9" stroke="#cbd5e1"/>\n'
        boxes += f'<text x="{x+12}" y="{y+28}" class="sub" font-weight="bold">{country}</text>\n'
        boxes += f'<text x="{x+12}" y="{y+52}" class="sub">{note}</text>\n'
    body = f"""
  <text x="40" y="36" class="title">Фасад разный — механизм один</text>
  <text x="40" y="58" class="sub">Где-то режут балл, где-то возраст, где-то льготу</text>
  {boxes}
"""
    wrap(OUT02 / "04_world_reforms.svg", body)


def main() -> None:
    OUT01.mkdir(parents=True, exist_ok=True)
    OUT02.mkdir(parents=True, exist_ok=True)
    demography_lines()
    tfr_countries()
    korea_wave()
    africa_tfr()
    pension_formula()
    ball_cost()
    moratorium()
    world_reforms()
    print("graphics ok:", OUT01, OUT02)


if __name__ == "__main__":
    main()
