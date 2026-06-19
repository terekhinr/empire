#!/usr/bin/env python3
"""Generate 1920×1080 graphics for YT-000 pension pilot (in-frame overlays)."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(_ROOT / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

OUT = _ROOT / "data" / "pension" / "video" / "graphics" / "yt-000"
FLAG_DIR = OUT / "assets" / "flags"
OUT.mkdir(parents=True, exist_ok=True)

BG = "#0d1117"
PANEL = "#161b22"
GRID = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#d4a853"
DANGER = "#f85149"
INFO = "#58a6ff"
OK = "#3fb950"
WARN = "#d29922"

W, H = 19.2, 10.8
DPI = 100

# Layout bands — header / plot / insight strip / footer never overlap
MARGIN_L, MARGIN_R = 0.08, 0.92
TITLE_Y = 0.94
SUBTITLE_Y = 0.895
PLOT_BOTTOM = 0.22
PLOT_TOP = 0.76
INSIGHT_Y = 0.17
SOURCE_Y = 0.07
BRAND_Y = 0.07

WATERMARK = "НА ПЕНСИЮ НИКОГДА"

# ISO 3166-1 alpha-2 for flagcdn.com
FLAG_CODES = {
    "RU": "ru",
    "GB": "gb",
    "UK": "gb",
    "US": "us",
    "SE": "se",
    "EU": "eu",
    "GR": "gr",
    "DE": "de",
    "FR": "fr",
    "JP": "jp",
    "CL": "cl",
    "SG": "sg",
}


def _new_figure() -> plt.Figure:
    return plt.figure(figsize=(W, H), facecolor=BG, dpi=DPI)


def _header(fig: plt.Figure, title: str, subtitle: str = "") -> None:
    fig.text(
        MARGIN_L,
        TITLE_Y,
        title,
        color=TEXT,
        fontsize=30,
        fontweight="bold",
        ha="left",
        va="top",
    )
    if subtitle:
        fig.text(
            MARGIN_L,
            SUBTITLE_Y,
            subtitle,
            color=MUTED,
            fontsize=16,
            ha="left",
            va="top",
            linespacing=1.25,
        )


def _footer(fig: plt.Figure, source: str = "") -> None:
    if source:
        fig.text(
            MARGIN_L,
            SOURCE_Y,
            source,
            color=MUTED,
            fontsize=11,
            ha="left",
            va="bottom",
        )
    fig.text(
        MARGIN_R,
        BRAND_Y,
        WATERMARK,
        color=MUTED,
        fontsize=12,
        ha="right",
        va="bottom",
        alpha=0.85,
    )


def _insight(fig: plt.Figure, text: str, *, color: str = TEXT, edge: str = GRID, ha: str = "left") -> None:
    """One-line insight strip between plot and footer — never on top of chart."""
    fig.text(
        MARGIN_L if ha == "left" else MARGIN_R,
        INSIGHT_Y,
        text,
        color=color,
        fontsize=15,
        ha=ha,
        va="center",
        linespacing=1.3,
        bbox=dict(boxstyle="round,pad=0.35", facecolor=PANEL, edgecolor=edge, linewidth=1.2),
    )


def _plot_rect() -> list[float]:
    return [MARGIN_L, PLOT_BOTTOM, MARGIN_R - MARGIN_L, PLOT_TOP - PLOT_BOTTOM]


def _style_plot_ax(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=16)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, axis="y", color=GRID, alpha=0.35, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, name: str) -> Path:
    path = OUT / name
    fig.savefig(path, dpi=DPI, facecolor=BG, edgecolor="none", bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f"  → {path.relative_to(_ROOT)}")
    return path


def _ensure_flag(iso2: str) -> Path | None:
    FLAG_DIR.mkdir(parents=True, exist_ok=True)
    path = FLAG_DIR / f"{iso2}.png"
    if path.is_file() and path.stat().st_size > 200:
        return path
    url = f"https://flagcdn.com/w80/{iso2}.png"
    try:
        urllib.request.urlretrieve(url, path)  # noqa: S310
        return path if path.stat().st_size > 200 else None
    except OSError:
        return None


def _flag_image(country_key: str, *, zoom: float = 0.22) -> OffsetImage | None:
    iso = FLAG_CODES.get(country_key.upper())
    if not iso:
        return None
    path = _ensure_flag(iso)
    if not path:
        return None
    img = plt.imread(path)
    return OffsetImage(img, zoom=zoom)


def _annotate_flag(ax: plt.Axes, country_key: str, xy: tuple[float, float], zoom: float = 0.2) -> None:
    oi = _flag_image(country_key, zoom=zoom)
    if oi:
        ax.add_artist(AnnotationBbox(oi, xy, frameon=False, xycoords="data"))


def chart_ipk_rub() -> None:
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    values = [87.24, 93.0, 98.86, 118.10, 123.77, 133.05, 145.69, 156.76]
    fig = _new_figure()
    _header(
        fig,
        "Стоимость пенсионного балла (ИПК) в России",
        "Сколько рублей платят за 1 балл — решает бюджет (ФЗ-400), не вы",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    ax.plot(years, values, color=ACCENT, linewidth=3.5, marker="o", markersize=9, zorder=3)
    ax.fill_between(years, values, alpha=0.12, color=ACCENT)
    for y, v in zip(years, values):
        if y not in (2019, 2023, 2026):
            continue
        ax.annotate(
            f"{v:.2f} ₽",
            (y, v),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            color=TEXT,
            fontsize=14,
            fontweight="bold",
        )
    ax.set_ylabel("₽ за 1 балл", color=MUTED, fontsize=16)
    ax.set_xlim(2018.4, 2026.6)
    ax.set_ylim(65, 175)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=0)
    oi = _flag_image("RU", zoom=0.35)
    if oi:
        ax.add_artist(AnnotationBbox(oi, (2026.15, 168), frameon=False, xycoords="data"))
    _insight(
        fig,
        "Вы копите баллы (права). Цену в рублях каждый год пишут в законе о бюджете СФР.",
        edge=ACCENT,
    )
    _footer(fig, "Источник: 350-ФЗ ч.7 ст.10; 2026 — бюджет СФР")
    _save(fig, "01_ipk_cost_russia.png")


def chart_uk_wfp() -> None:
    labels = ["2023/24", "2024/25"]
    values = [10.6, 1.3]
    fig = _new_figure()
    _header(
        fig,
        "Великобритания: Winter Fuel Payment",
        "Сколько пенсионеров получали зимнюю помощь на отопление (млн)",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    bars = ax.bar(labels, values, color=[INFO, DANGER], width=0.42)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + 0.45,
            f"{v:.1f} млн",
            ha="center",
            color=TEXT,
            fontsize=22,
            fontweight="bold",
        )
    ax.set_ylim(0, 12)
    ax.set_ylabel("млн человек", color=MUTED, fontsize=16)
    ax.text(
        0.5,
        5.8,
        "↓ 88% за один год",
        ha="center",
        fontsize=28,
        color=DANGER,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=DANGER, alpha=0.9),
    )
    oi = _flag_image("GB", zoom=0.32)
    if oi:
        ax.add_artist(AnnotationBbox(oi, (1.45, 10.5), frameon=False, xycoords="data"))
    _insight(fig, "С зимы 2024/25 льготой охвачено ≈13% пенсионеров 66+ (остальные — без помощи).", edge=WARN)
    _footer(fig, "Источник: DWP, Winter Fuel Payment statistics 2024/25")
    _save(fig, "02_uk_winter_fuel_payment.png")


def chart_uk_cold_deaths() -> None:
    episodes = ["20–21\nноя", "2–3\nянв", "7–12\nянв"]
    deaths = [421, 493, 1630]
    fig = _new_figure()
    _header(
        fig,
        "Англия: смерти, связанные с холодом",
        "Зима 2024/25 · оценка UKHSA (модель избыточной смертности)",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    ax.bar(episodes, deaths, color=[INFO, WARN, DANGER], width=0.48)
    for i, d in enumerate(deaths):
        ax.text(i, d + 70, str(d), ha="center", color=TEXT, fontsize=20, fontweight="bold")
    ax.set_ylim(0, 1900)
    ax.set_ylabel("человек (оценка)", color=MUTED, fontsize=16)
    ax.text(
        2.0,
        1750,
        "Σ 2 544",
        ha="right",
        fontsize=26,
        color=DANGER,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor=DANGER),
    )
    _insight(fig, "Это не «864 замёрзли дома» — статистика холода и недогрева за сезон.", edge=DANGER)
    _footer(fig, "Источник: UKHSA Cold mortality report, 18.02.2026")
    _save(fig, "03_uk_cold_mortality_episodes.png")


def chart_uk_dashboard() -> None:
    fig = _new_figure()
    _header(
        fig,
        "Великобритания: один зимний сезон",
        "Три официальные цифры — запомнить связку, не одну строку",
    )
    metrics = [
        ("2 544", "смерти,\nсвязанные\nс холодом", DANGER, "UKHSA"),
        ("11%", "домохозяйств\nне могут\nнормально греть дом", WARN, "DESNZ"),
        ("13%", "пенсионеров 66+\nполучили WFP\n(было почти все)", INFO, "DWP"),
    ]
    col_w = (MARGIN_R - MARGIN_L) / 3
    for col, (val, label, color, src) in enumerate(metrics):
        left = MARGIN_L + col * col_w + 0.015
        width = col_w - 0.03
        ax = fig.add_axes([left, PLOT_BOTTOM + 0.02, width, PLOT_TOP - PLOT_BOTTOM - 0.04])
        ax.set_facecolor(PANEL)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        if col == 0:
            oi = _flag_image("GB", zoom=0.55)
            if oi:
                ax.add_artist(AnnotationBbox(oi, (0.12, 0.92), frameon=False, xycoords="axes fraction"))
        ax.text(0.5, 0.72, val, ha="center", va="center", fontsize=44, color=color, fontweight="bold")
        ax.text(0.5, 0.42, label, ha="center", va="center", fontsize=15, color=TEXT, linespacing=1.35)
        ax.text(0.5, 0.10, src, ha="center", va="center", fontsize=11, color=MUTED)
    _insight(fig, "В ленте — «пенсионер на яхте». В отчёте — холод, fuel poverty и срез WFP.", edge=WARN)
    _footer(fig, "Зима 2024/25, Англия")
    _save(fig, "04_uk_winter_dashboard.png")


def chart_oecd_poverty() -> None:
    groups = ["Все\nвозрасты", "65+", "75+"]
    rates = [11.5, 14.8, 17.2]
    fig = _new_figure()
    _header(
        fig,
        "Относительная бедность в OECD",
        "Доля людей с доходом ниже 50% медианы по стране",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    x = range(len(groups))
    ax.bar(x, rates, color=[INFO, WARN, DANGER], width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, color=MUTED, fontsize=15)
    for i, r in enumerate(rates):
        ax.text(i, r + 0.4, f"{r:.1f}%", ha="center", color=TEXT, fontsize=22, fontweight="bold")
    ax.set_ylim(0, 20)
    ax.set_ylabel("% населения", color=MUTED, fontsize=16)
    ax.axhline(11.5, color=MUTED, linestyle="--", linewidth=1, alpha=0.45)
    ax.text(2.35, 11.8, "уровень «все»", fontsize=11, color=MUTED, ha="right")
    _insight(
        fig,
        "Чем старше когорта — тем выше бедность. «Богатый европейский дед» — хвост, не медиана.",
        edge=WARN,
    )
    _footer(fig, "Источник: OECD Pensions at a Glance 2025")
    _save(fig, "05_oecd_old_age_poverty.png")


def chart_us_retirement_donut() -> None:
    fig = _new_figure()
    _header(
        fig,
        "США: домохозяйства 55–64 лет",
        "Есть ли пенсионный счёт (401k, IRA) — не «сколько накопили все»",
    )
    ax_pie = fig.add_axes([0.10, PLOT_BOTTOM + 0.02, 0.38, PLOT_TOP - PLOT_BOTTOM - 0.02])
    wedges, _, autotexts = ax_pie.pie(
        [57, 43],
        labels=["Есть счёт", "Нет счёта"],
        colors=[OK, DANGER],
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.75,
        labeldistance=1.05,
        textprops={"color": TEXT, "fontsize": 16},
        wedgeprops=dict(width=0.36, edgecolor=BG, linewidth=2),
    )
    for t in autotexts:
        t.set_fontsize(20)
        t.set_fontweight("bold")
        t.set_color(BG)
    ax_pie.set_aspect("equal")
    oi = _flag_image("US", zoom=0.4)
    if oi:
        ax_pie.add_artist(AnnotationBbox(oi, (-0.95, 1.15), frameon=False, xycoords="axes fraction"))

    ax_txt = fig.add_axes([0.52, PLOT_BOTTOM, 0.40, PLOT_TOP - PLOT_BOTTOM])
    ax_txt.axis("off")
    lines = [
        ("57%", "домохозяйств", "есть счёт", OK),
        ("43%", "домохозяйств", "без счёта", DANGER),
        ("", "", "", TEXT),
        ("$185 000", "медиана", "у кого счёт есть", MUTED),
        ("$87 000", "медиана", "по всем HH 55–64", MUTED),
    ]
    y = 0.92
    for a, b, c, col in lines:
        if not a:
            y -= 0.06
            continue
        ax_txt.text(0, y, a, fontsize=28 if "%" in a or "$" in a else 18, color=col, fontweight="bold", va="top")
        ax_txt.text(0.42, y + 0.02, f"{b}\n{c}", fontsize=14, color=MUTED, va="top", linespacing=1.2)
        y -= 0.22

    _insight(fig, "Гольф и яхта — у верхнего хвоста. У медианы — несколько лет скромной жизни.", edge=INFO)
    _footer(fig, "Источник: Federal Reserve SCF 2022 / CRS IF12928")
    _save(fig, "06_us_retirement_accounts_55_64.png")


def chart_oecd_replacement() -> None:
    labels = [
        "Только\nгосударство",
        "Все обязательные\nсхемы",
        "Обязательные\n+ добровольные",
    ]
    values = [43, 52, 57]
    fig = _new_figure()
    _header(
        fig,
        "OECD: сколько пенсия замещает зарплату",
        "При полной карьере и среднем заработке · % от прежней зарплаты (валовая оценка)",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, color=[DANGER, WARN, INFO], height=0.55)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color=MUTED, fontsize=14)
    ax.set_xlim(0, 72)
    for bar, v in zip(bars, values):
        ax.text(
            v + 1.5,
            bar.get_y() + bar.get_height() / 2,
            f"{v}%",
            va="center",
            color=TEXT,
            fontsize=20,
            fontweight="bold",
        )
    ax.axvline(100, color=MUTED, linestyle=":", linewidth=1, alpha=0.4)
    ax.text(101, 2.2, "100% = прежняя зарплата", fontsize=11, color=MUTED, va="center")
    ax.set_xlabel("% замещения", color=MUTED, fontsize=15)
    ax.grid(True, axis="x", color=GRID, alpha=0.35)
    ax.grid(False, axis="y")
    _insight(fig, "Даже «полный комплект» в OECD — около половины прежнего дохода, не «как на работе».", edge=WARN)
    _footer(fig, "Источник: OECD Pensions at a Glance 2025")
    _save(fig, "07_oecd_replacement_rates.png")


def chart_demography_workers() -> None:
    eras = ["1950-е", "Сейчас", "2030-е"]
    ratios = [9, 2.5, 1.8]
    fig = _new_figure()
    _header(
        fig,
        "Работающих на одного пенсионера",
        "Упрощённо для развитых стран · чем ниже — тем хуже для PAYG",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    ax.bar(eras, ratios, color=[OK, WARN, DANGER], width=0.45)
    for i, r in enumerate(ratios):
        label = f"~{int(r)}" if r >= 3 else f"~{r:.1f}"
        ax.text(i, r + 0.3, label, ha="center", color=TEXT, fontsize=24, fontweight="bold")
    ax.set_ylim(0, 10)
    ax.set_ylabel("человек на 1 пенсионера", color=MUTED, fontsize=16)
    _insight(
        fig,
        "PAYG = конвейер: сегодняшние зарплаты платят сегодняшним пенсионерам. Мало «подающих» — конвейер встаёт.",
        edge=DANGER,
    )
    _footer(fig, "Источник: OECD / книга «На пенсию НИКОГДА»")
    _save(fig, "08_demography_workers_per_pensioner.png")


def chart_eu_gender_gap() -> None:
    fig = _new_figure()
    _header(
        fig,
        "Европейский союз: разрыв пенсий",
        "Средняя пенсия женщин 65+ относительно мужчин, 2024",
    )
    ax = fig.add_axes(_plot_rect())
    _style_plot_ax(ax)
    ax.barh([0], [-24.5], color=DANGER, height=0.4)
    ax.set_yticks([0])
    ax.set_yticklabels(["Женщины получают меньше"], color=TEXT, fontsize=16)
    ax.set_xlim(-30, 5)
    ax.axvline(0, color=GRID, linewidth=2)
    ax.text(-12.2, 0, "−24,5%", ha="center", va="center", fontsize=34, color=TEXT, fontweight="bold")
    ax.set_xlabel("разница, %", color=MUTED, fontsize=15)
    ax.grid(True, axis="x")
    oi = _flag_image("EU", zoom=0.38)
    if oi:
        ax.add_artist(AnnotationBbox(oi, (-28, 0.55), frameon=False, xycoords="data"))
    _insight(fig, "В 22 из 27 стран ЕС женщины-пенсионерки беднее мужчин (Eurostat AROP).", edge=DANGER)
    _footer(fig, "Источник: Eurostat ilc_pnp13, 2024")
    _save(fig, "09_eu_gender_pension_gap.png")


def table_countries_compare() -> None:
    fig = _new_figure()
    _header(
        fig,
        "Один механизм — разный фасад",
        "Сравнение: что обещают · кто режет · цифра-якорь",
    )
    ax = fig.add_axes([MARGIN_L, PLOT_BOTTOM, MARGIN_R - MARGIN_L, PLOT_TOP - PLOT_BOTTOM])
    ax.set_xlim(0, 10)
    n_rows = 6
    ax.set_ylim(0, n_rows + 1.2)
    ax.axis("off")

    col_x = [0.0, 1.1, 3.0, 5.2, 7.4]
    headers = ["", "Обещание", "Кто режет риск", "Якорь"]
    for hx, ht in zip(col_x[1:], headers[1:]):
        ax.text(hx, n_rows + 0.85, ht, fontsize=14, color=ACCENT, fontweight="bold", va="center")

    data = [
        ("RU", "Россия", "ИПК × цена балла + фикс", "Бюджет / Госдума", "156,76 ₽/балл\nНЧ с 2014"),
        ("GB", "Великобритания", "State Pension + WFP", "Парламент", "2 544 cold\nWFP −88%"),
        ("US", "США", "Social Security + 401(k)", "Конгресс, рынок", "43% без счёта\n(55–64)"),
        ("SE", "Швеция", "NDC-счета", "Автотормоз", "Срез индексации"),
        ("EU", "Евросоюз", "Гос. + проф.", "Демография", "Бедность 65+:\n14,8%"),
        ("GR", "Греция", "Гос. пенсии", "Меморандум ЕС", "−10% (2010–11)"),
    ]
    for row_i, (code, name, prom, who, anchor) in enumerate(data):
        y = n_rows - row_i - 0.15
        if row_i % 2 == 0:
            ax.add_patch(
                mpatches.Rectangle(
                    (0, y - 0.42),
                    10,
                    0.88,
                    facecolor=PANEL if row_i % 2 else "#1c2128",
                    edgecolor="none",
                    alpha=0.9,
                )
            )
        oi = _flag_image(code, zoom=0.28)
        if oi:
            ax.add_artist(AnnotationBbox(oi, (0.35, y), frameon=False, xycoords="data"))
        ax.text(1.05, y, name, fontsize=14, color=ACCENT, fontweight="bold", va="center")
        ax.text(3.0, y, prom, fontsize=12, color=TEXT, va="center", linespacing=1.2)
        ax.text(5.2, y, who, fontsize=12, color=MUTED, va="center", linespacing=1.2)
        ax.text(7.4, y, anchor, fontsize=12, color=TEXT, va="center", linespacing=1.2)

    _insight(fig, "Страна меняет этикетку. Двигатель один: демография + политика + риск на вас.", edge=ACCENT)
    _footer(fig, "ФЗ-400/350 · UKHSA · DWP · Fed SCF · OECD · Eurostat")
    _save(fig, "10_table_countries_one_mechanism.png")


def infographic_nowhere() -> None:
    fig = _new_figure()
    _header(
        fig,
        "ЕХАТЬ НЕКУДА",
        "Фасад разный · механизм один · выход — столб 3 (личный план)",
    )
    ax = fig.add_axes([MARGIN_L, PLOT_BOTTOM, MARGIN_R - MARGIN_L, PLOT_TOP - PLOT_BOTTOM])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    items = [
        ("RU", "Россия", "Баллы", "цена из бюджета"),
        ("GB", "Британия", "Тепло", "холод + WFP"),
        ("US", "США", "401(k)", "рынок + SS"),
        ("SE", "Швеция", "NDC", "автотормоз"),
        ("EU", "ЕС", "Медиана", "не Instagram-хвост"),
    ]
    for i, (code, name, head, sub) in enumerate(items):
        x = 1.0 + i * 1.85
        rect = mpatches.FancyBboxPatch(
            (x - 0.72, 2.0),
            1.44,
            2.35,
            boxstyle="round,pad=0.06,rounding_size=0.1",
            facecolor=PANEL,
            edgecolor=GRID,
            linewidth=1.5,
        )
        ax.add_patch(rect)
        oi = _flag_image(code, zoom=0.32)
        if oi:
            ax.add_artist(AnnotationBbox(oi, (x, 4.05), frameon=False, xycoords="data"))
        ax.text(x, 3.55, name, ha="center", fontsize=13, color=ACCENT, fontweight="bold")
        ax.text(x, 3.05, head, ha="center", fontsize=17, color=TEXT, fontweight="bold")
        ax.text(x, 2.45, sub, ha="center", fontsize=11, color=MUTED)

    ax.annotate(
        "",
        xy=(9.1, 1.35),
        xytext=(1.0, 1.35),
        arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=2.5),
    )
    ax.text(5.0, 1.55, "один двигатель: демография · политика · инфляция", ha="center", fontsize=13, color=ACCENT)

    pillars = [("Тело", OK), ("Кэшфлоу", INFO), ("Семья / земля", WARN)]
    px = [2.2, 5.0, 7.8]
    for (label, col), x in zip(pillars, px):
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x - 0.9, 0.15),
                1.8,
                0.75,
                boxstyle="round,pad=0.05",
                facecolor=BG,
                edgecolor=col,
                linewidth=1.8,
            )
        )
        ax.text(x, 0.52, label, ha="center", fontsize=14, color=col, fontweight="bold")

    ax.text(5.0, 0.02, "Столб 3 — ваш, не государственный", ha="center", fontsize=12, color=MUTED)
    _footer(fig, "Не ИИР · пилот YT-000")
    _save(fig, "11_infographic_nowhere_to_run.png")


def slide_hemingway_quote() -> None:
    fig = _new_figure()
    fig.text(
        0.5,
        0.62,
        "«Как всё это будет происходить?\nСначала постепенно,\nа потом внезапно»",
        ha="center",
        va="center",
        fontsize=36,
        color=TEXT,
        fontstyle="italic",
        linespacing=1.45,
        bbox=dict(boxstyle="round,pad=0.7", facecolor=PANEL, edgecolor=ACCENT, linewidth=2),
    )
    fig.text(0.5, 0.40, "— Эрнест Хемингуэй, «Фиеста»", ha="center", color=MUTED, fontsize=20)
    fig.text(
        0.5,
        0.30,
        "Так ломается пенсионное обещание: сначала индексация и «мягкие реформы», потом обрыв",
        ha="center",
        color=MUTED,
        fontsize=16,
        linespacing=1.3,
    )
    _footer(fig)
    _save(fig, "13_hemingway_quote.png")


def chart_stereotype_vs_reality() -> None:
    fig = _new_figure()
    _header(
        fig,
        "Два слоя одного распределения",
        "Слева — то, что показывает реклама · справа — медиана по OECD/EU/UK",
    )
    panels = [
        ("Стереотип (хвост 5–10%)", OK, ["DB-пенсия 70–90-х", "Жильё куплено", "Полный стаж · чаще мужчины"]),
        ("Медиана (большинство)", DANGER, ["OECD 65+: 14,8% бедности", "ЕС: −25% пенсия женщин", "UK: 11% fuel poverty"]),
    ]
    for col, (title, color, lines) in enumerate(panels):
        left = MARGIN_L + col * (MARGIN_R - MARGIN_L) / 2 + 0.02
        width = (MARGIN_R - MARGIN_L) / 2 - 0.04
        ax = fig.add_axes([left, PLOT_BOTTOM + 0.02, width, PLOT_TOP - PLOT_BOTTOM - 0.02])
        ax.set_facecolor(PANEL)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.text(0.5, 0.94, title, ha="center", va="top", fontsize=19, color=color, fontweight="bold")
        y = 0.72
        for line in lines:
            ax.text(0.08, y, f"• {line}", fontsize=15, color=TEXT, va="top", linespacing=1.25)
            y -= 0.17
    _insight(fig, "Оба образа правдивы — но для разных людей. В кадре не путайте хвост и массу.", edge=ACCENT)
    _footer(fig, "OECD · Eurostat · DESNZ")
    _save(fig, "12_stereotype_vs_median.png")


def main() -> None:
    print(f"Output: {OUT}  |  flags: {FLAG_DIR}")
    chart_ipk_rub()
    chart_uk_wfp()
    chart_uk_cold_deaths()
    chart_uk_dashboard()
    chart_oecd_poverty()
    chart_us_retirement_donut()
    chart_oecd_replacement()
    chart_demography_workers()
    chart_eu_gender_gap()
    table_countries_compare()
    infographic_nowhere()
    chart_stereotype_vs_reality()
    slide_hemingway_quote()
    print(f"\nDone: {len(list(OUT.glob('*.png')))} PNG")


if __name__ == "__main__":
    main()
