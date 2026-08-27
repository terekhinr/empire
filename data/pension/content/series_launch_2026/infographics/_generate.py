#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Infographics for «На пенсию никогда» — exact figures, editorial dark theme."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("/root/projects/empire/data/pension/content/series_launch_2026/infographics")
OUT.mkdir(parents=True, exist_ok=True)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_S = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

BG = (20, 18, 16)
CARD = (31, 28, 24)
TEXT = (242, 237, 228)
MUTED = (154, 145, 134)
ACCENT = (232, 165, 75)
WARN = (196, 92, 62)
LINE = (58, 52, 44)
OK = (110, 168, 130)


def font(path, size):
    return ImageFont.truetype(path, size)


def new(w, h):
    im = Image.new("RGB", (w, h), BG)
    dr = ImageDraw.Draw(im)
    return im, dr


def footer(dr, w, h, src):
    dr.line((48, h - 64, w - 48, h - 64), fill=LINE, width=1)
    dr.text((48, h - 48), src, font=font(FONT, 18), fill=MUTED)
    dr.text((w - 48, h - 48), "На пенсию никогда", font=font(FONT, 18), fill=MUTED, anchor="ra")


def title(dr, text, y=40):
    dr.text((48, y), text, font=font(FONT_SB, 36), fill=TEXT)


def save(im, name):
    path = OUT / name
    im.save(path, "PNG", optimize=True)
    print("wrote", path.name, im.size)


# --- 1. IPK + FV ---
def fig_ipk():
    im, dr = new(1080, 1080)
    title(dr, "Страховая пенсия, 2026")
    dr.text((48, 100), "СФР · индексация с 1 января", font=font(FONT, 22), fill=MUTED)

    # big badge
    dr.rounded_rectangle((48, 180, 1032, 360), radius=24, fill=CARD)
    dr.text((80, 210), "индексация", font=font(FONT, 24), fill=MUTED)
    dr.text((80, 250), "7,6%", font=font(FONT_B, 96), fill=ACCENT)

    # two cards
    dr.rounded_rectangle((48, 400, 520, 780), radius=24, fill=CARD)
    dr.rounded_rectangle((560, 400, 1032, 780), radius=24, fill=CARD)
    dr.text((80, 440), "стоимость ИПК", font=font(FONT, 22), fill=MUTED)
    dr.text((80, 500), "156,76 ₽", font=font(FONT_B, 56), fill=TEXT)
    dr.text((80, 590), "один балл", font=font(FONT, 22), fill=MUTED)

    dr.text((592, 440), "фиксированная выплата", font=font(FONT, 22), fill=MUTED)
    dr.text((592, 500), "9 584,69 ₽", font=font(FONT_B, 48), fill=TEXT)
    dr.text((592, 590), "к страховой по старости", font=font(FONT, 22), fill=MUTED)

    dr.text((48, 840), "Формула: ИПК × стоимость коэффициента + фикса", font=font(FONT, 22), fill=MUTED)
    footer(dr, 1080, 1080, "sfr.gov.ru · 2026")
    save(im, "shared_ipk_2026.png")


def fig_tfr_ru():
    im, dr = new(1080, 1080)
    title(dr, "Рождаемость в России")
    dr.text((48, 100), "Суммарный коэффициент рождаемости", font=font(FONT, 22), fill=MUTED)

    # scale bar
    x0, x1, y = 80, 1000, 520
    dr.line((x0, y, x1, y), fill=LINE, width=6)
    # ticks 0, 1, 2, 2.5
    def x_at(v):
        return int(x0 + (x1 - x0) * (v / 2.5))

    for v, lab in [(0, "0"), (1, "1"), (2, "2"), (2.5, "2,5")]:
        x = x_at(v)
        dr.line((x, y - 12, x, y + 12), fill=MUTED, width=2)
        dr.text((x, y + 24), lab, font=font(FONT, 20), fill=MUTED, anchor="ma")

    # threshold 2.1
    xt = x_at(2.1)
    dr.line((xt, 280, xt, y), fill=OK, width=3)
    dr.text((xt, 250), "порог 2,1", font=font(FONT_B, 24), fill=OK, anchor="ma")

    # point 1.374
    xp = x_at(1.374)
    dr.ellipse((xp - 16, y - 16, xp + 16, y + 16), fill=WARN)
    dr.text((xp, 600), "1,374", font=font(FONT_B, 48), fill=WARN, anchor="ma")
    dr.text((xp, 660), "конец 2025 · оперативно", font=font(FONT, 20), fill=MUTED, anchor="ma")

    # 2015 mark
    x15 = x_at(1.77)
    dr.ellipse((x15 - 8, y - 8, x15 + 8, y + 8), fill=ACCENT)
    dr.text((x15, 720), "2015: 1,77", font=font(FONT, 20), fill=ACCENT, anchor="ma")

    footer(dr, 1080, 1080, "Росстат / Ведомости · без ряда новых регионов")
    save(im, "shared_tfr_ru.png")


def fig_vanguard():
    im, dr = new(1600, 900)
    title(dr, "США, пенсионные счета 55–64")
    dr.text((48, 100), "Vanguard How America Saves 2025 · участники планов", font=font(FONT, 22), fill=MUTED)

    # bars
    max_v = 271320
    base_y = 720
    def bar(x, val, color, label, sub):
        h = int(420 * (val / max_v))
        dr.rounded_rectangle((x, base_y - h, x + 280, base_y), radius=16, fill=color)
        dr.text((x + 140, base_y - h - 50), f"{val:,}".replace(",", " ") + " $", font=font(FONT_B, 32), fill=TEXT, anchor="ma")
        dr.text((x + 140, base_y + 20), label, font=font(FONT_B, 26), fill=TEXT, anchor="ma")
        dr.text((x + 140, base_y + 55), sub, font=font(FONT, 20), fill=MUTED, anchor="ma")

    bar(200, 271320, CARD, "среднее", "хвост богатых тянет вверх")
    # accent for median
    bar(560, 95642, (70, 55, 35), "середина ряда", "типичный участник")
    # fill median bar with accent top feel - redraw
    h = int(420 * (95642 / max_v))
    dr.rounded_rectangle((560, base_y - h, 840, base_y), radius=16, fill=ACCENT)
    dr.text((700, base_y - h - 50), "95 642 $", font=font(FONT_B, 32), fill=TEXT, anchor="ma")
    dr.text((700, base_y + 20), "середина ряда", font=font(FONT_B, 26), fill=TEXT, anchor="ma")
    dr.text((700, base_y + 55), "типичный участник", font=font(FONT, 20), fill=MUTED, anchor="ma")

    # inset
    dr.rounded_rectangle((1000, 220, 1520, 480), radius=20, fill=CARD)
    dr.text((1260, 280), "есть пенсионный счёт", font=font(FONT, 22), fill=MUTED, anchor="ma")
    dr.text((1260, 340), "57%", font=font(FONT_B, 72), fill=WARN, anchor="ma")
    dr.text((1260, 420), "домохозяйства 55–64 · SCF 2022", font=font(FONT, 18), fill=MUTED, anchor="ma")

    footer(dr, 1600, 900, "Vanguard HAS 2025 · CRS / Federal Reserve SCF 2022")
    save(im, "shared_vanguard_5564.png")


def fig_oecd_poverty():
    im, dr = new(1080, 1080)
    title(dr, "ОЭСР: бедность в старости")
    dr.text((48, 100), "Относительная бедность · Pensions at a Glance 2025", font=font(FONT, 22), fill=MUTED)

    items = [
        ("всё население", 11.5, MUTED),
        ("65+", 14.8, ACCENT),
        ("75+", 17.2, WARN),
    ]
    y0 = 280
    for i, (lab, pct, col) in enumerate(items):
        y = y0 + i * 180
        dr.text((80, y), lab, font=font(FONT, 28), fill=TEXT)
        wbar = int(700 * (pct / 20))
        dr.rounded_rectangle((80, y + 50, 80 + wbar, y + 100), radius=12, fill=col)
        dr.text((100 + wbar, y + 60), f"{pct}%".replace(".", ","), font=font(FONT_B, 36), fill=TEXT)

    footer(dr, 1080, 1080, "oecd.org · Pensions at a Glance 2025")
    save(im, "shared_oecd_poverty.png")


def fig_keyrate():
    im, dr = new(1080, 1080)
    title(dr, "Ключевая ставка ЦБ")
    dr.text((48, 100), "Решение от 24.07.2026", font=font(FONT, 22), fill=MUTED)
    dr.rounded_rectangle((48, 200, 1032, 520), radius=28, fill=CARD)
    dr.text((540, 280), "14,00%", font=font(FONT_B, 120), fill=ACCENT, anchor="ma")
    dr.text((540, 420), "годовых", font=font(FONT, 28), fill=MUTED, anchor="ma")

    dr.rounded_rectangle((48, 560, 520, 820), radius=20, fill=CARD)
    dr.rounded_rectangle((560, 560, 1032, 820), radius=20, fill=CARD)
    dr.text((284, 620), "короткий запас", font=font(FONT_B, 26), fill=OK, anchor="ma")
    dr.text((284, 680), "стоянка денег\nзаметна", font=font(FONT, 24), fill=TEXT, anchor="ma", align="center")
    dr.text((796, 620), "ипотека под сдачу", font=font(FONT_B, 26), fill=WARN, anchor="ma")
    dr.text((796, 680), "часто доплачивать\nбанку", font=font(FONT, 24), fill=TEXT, anchor="ma", align="center")

    dr.text((48, 860), "Прогноз ЦБ 2026: средняя ставка 14,5–14,6% · инфляция 6–7%", font=font(FONT, 20), fill=MUTED)
    footer(dr, 1080, 1080, "cbr.ru/press/keypr")
    save(im, "shared_keyrate_14.png")


def fig_addendum_roof():
    im, dr = new(1080, 1080)
    title(dr, "Добавка и кровля")
    dr.text((48, 100), "Две разные роли денег на старости", font=font(FONT, 22), fill=MUTED)

    # foundation
    dr.rounded_rectangle((120, 720, 960, 860), radius=16, fill=ACCENT)
    dr.text((540, 770), "СВОЙ ПОТОК — фундамент / кровля", font=font(FONT_B, 28), fill=BG, anchor="ma")

    # house body
    dr.rounded_rectangle((220, 420, 860, 700), radius=12, fill=CARD)
    dr.text((540, 520), "жизнь", font=font(FONT_B, 36), fill=TEXT, anchor="ma")

    # boiler side
    dr.rounded_rectangle((80, 260, 420, 400), radius=16, fill=CARD)
    dr.text((250, 300), "котёл СФР", font=font(FONT_B, 28), fill=TEXT, anchor="ma")
    dr.text((250, 345), "госпенсия", font=font(FONT, 22), fill=MUTED, anchor="ma")

    # arrow
    dr.polygon([(430, 320), (520, 300), (520, 340)], fill=WARN)
    dr.text((540, 280), "добавка", font=font(FONT_B, 24), fill=WARN)

    dr.text((540, 940), "Путать строки — главный источник обид", font=font(FONT, 22), fill=MUTED, anchor="ma")
    footer(dr, 1080, 1080, "схема автора · не ИИР")
    save(im, "00_addendum_vs_roof.png")


def fig_paygo():
    im, dr = new(1080, 1080)
    title(dr, "Солидарный котёл")
    dr.text((48, 100), "Pay-as-you-go: не личная банка с твоим именем", font=font(FONT, 22), fill=MUTED)

    dr.ellipse((390, 380, 690, 680), outline=ACCENT, width=8)
    dr.text((540, 510), "КОТЁЛ", font=font(FONT_B, 40), fill=ACCENT, anchor="ma")
    dr.text((540, 560), "сейчас", font=font(FONT, 24), fill=MUTED, anchor="ma")

    dr.rounded_rectangle((80, 280, 340, 400), radius=16, fill=CARD)
    dr.text((210, 320), "работники", font=font(FONT_B, 28), fill=TEXT, anchor="ma")
    dr.text((210, 360), "взносы сегодня", font=font(FONT, 20), fill=MUTED, anchor="ma")

    dr.rounded_rectangle((740, 280, 1000, 400), radius=16, fill=CARD)
    dr.text((870, 320), "пенсионеры", font=font(FONT_B, 28), fill=TEXT, anchor="ma")
    dr.text((870, 360), "выплаты сегодня", font=font(FONT, 20), fill=MUTED, anchor="ma")

    # arrows
    dr.line((340, 340, 400, 480), fill=OK, width=6)
    dr.line((680, 480, 740, 340), fill=WARN, width=6)

    dr.text((540, 760), "Сужается основание → крутят возраст,\nформулу, налоги", font=font(FONT, 26), fill=TEXT, anchor="ma", align="center")
    footer(dr, 1080, 1080, "логика распределительных систем · OECD / ООН")
    save(im, "01_paygo_pot.png")


def fig_formula():
    im, dr = new(1600, 900)
    title(dr, "Как считают страховую пенсию")
    dr.text((48, 100), "СФР · 400-ФЗ", font=font(FONT, 22), fill=MUTED)
    dr.rounded_rectangle((80, 280, 1520, 620), radius=28, fill=CARD)
    formula = "ИПК  ×  156,76 ₽  +  9 584,69 ₽"
    dr.text((800, 400), formula, font=font(FONT_B, 52), fill=TEXT, anchor="ma")
    dr.text((800, 500), "баллы × цена балла + фиксированная выплата", font=font(FONT, 28), fill=MUTED, anchor="ma")
    dr.text((800, 700), "Цена балла и фикса задаются законом / индексацией — не корзиной у дома", font=font(FONT, 24), fill=MUTED, anchor="ma")
    footer(dr, 1600, 900, "sfr.gov.ru · 2026")
    save(im, "01_formula.png")


def fig_moratorium():
    im, dr = new(1600, 900)
    title(dr, "Мораторий длиннее школы")
    dr.text((48, 100), "Накопительная часть обязательных взносов → в страховую", font=font(FONT, 22), fill=MUTED)

    y = 420
    dr.line((120, y, 1480, y), fill=LINE, width=8)
    points = [(200, "2014", "старт\n351-ФЗ", WARN), (900, "…", "продления", MUTED), (1400, "2026", "всё ещё\nрежим", ACCENT)]
    for x, year, lab, col in points:
        dr.ellipse((x - 18, y - 18, x + 18, y + 18), fill=col)
        dr.text((x, y - 80), year, font=font(FONT_B, 36), fill=col, anchor="ma")
        dr.text((x, y + 50), lab, font=font(FONT, 24), fill=TEXT, anchor="ma", align="center")

    dr.rounded_rectangle((400, 600, 1200, 760), radius=16, fill=CARD)
    dr.text((800, 650), "Ребёнок 1 класса в 2014 → выпускник в 2026", font=font(FONT_B, 28), fill=TEXT, anchor="ma")
    dr.text((800, 710), "«Пауза» живёт дольше школьной скамьи", font=font(FONT, 24), fill=MUTED, anchor="ma")
    footer(dr, 1600, 900, "351-ФЗ и последующие продления")
    save(im, "01_moratorium_timeline.png")


def fig_korea():
    im, dr = new(1080, 1080)
    title(dr, "Южная Корея · СКР")
    dr.text((48, 100), "Даже после отскока — пропасть до 2,1", font=font(FONT, 22), fill=MUTED)
    dr.rounded_rectangle((48, 220, 1032, 620), radius=28, fill=CARD)
    dr.text((540, 360), "0,80", font=font(FONT_B, 140), fill=WARN, anchor="ma")
    dr.text((540, 500), "предв. 2025", font=font(FONT, 28), fill=MUTED, anchor="ma")
    dr.text((200, 700), "2023: 0,72", font=font(FONT, 28), fill=MUTED)
    dr.text((540, 700), "2024: 0,75", font=font(FONT, 28), fill=MUTED, anchor="ma")
    dr.text((880, 700), "порог: 2,1", font=font(FONT_B, 28), fill=OK, anchor="ra")
    footer(dr, 1080, 1080, "Reuters / Yonhap · 2025–2026")
    save(im, "01_korea_080.png")


def fig_goal():
    im, dr = new(1080, 1080)
    title(dr, "Цель — в рублях на месяц")
    dr.text((48, 100), "Не «много денег», а закрытая нужда", font=font(FONT, 22), fill=MUTED)
    dr.rounded_rectangle((120, 300, 960, 620), radius=28, outline=ACCENT, width=4)
    dr.text((540, 400), "________ ₽ / мес", font=font(FONT_B, 56), fill=TEXT, anchor="ma")
    dr.text((540, 500), "еда · жильё · лекарства · минимальный смысл", font=font(FONT, 24), fill=MUTED, anchor="ma")
    dr.text((540, 720), "Сначала число на листке — потом инструменты", font=font(FONT, 26), fill=MUTED, anchor="ma")
    footer(dr, 1080, 1080, "метод автора · не ГОСТ")
    save(im, "02_goal_rub.png")


def fig_norm():
    im, dr = new(1080, 1080)
    title(dr, "Норма сбережений")
    dr.text((48, 100), "Правда из выписки, не из ощущений", font=font(FONT, 22), fill=MUTED)
    dr.rounded_rectangle((80, 280, 1000, 560), radius=24, fill=CARD)
    dr.text((540, 380), "отложено  ÷  пришло", font=font(FONT_B, 48), fill=ACCENT, anchor="ma")
    dr.text((540, 470), "среднее за 3 месяца", font=font(FONT, 28), fill=MUTED, anchor="ma")
    for i, lab in enumerate(["месяц 1", "месяц 2", "месяц 3"]):
        x = 180 + i * 280
        dr.rounded_rectangle((x, 620, x + 200, 780), radius=16, fill=CARD)
        dr.text((x + 100, 680), lab, font=font(FONT, 24), fill=TEXT, anchor="ma")
    footer(dr, 1080, 1080, "учебный жест · автоперевод в день зарплаты")
    save(im, "02_savings_rate.png")


def fig_baskets():
    im, dr = new(1600, 900)
    title(dr, "Четыре корзины — рамка")
    dr.text((48, 100), "Не сигнал купить бумагу · не доли в процентах", font=font(FONT, 22), fill=MUTED)
    boxes = [
        ("Выплаты\nпо бумагам", "крепкий бизнес\nради потока"),
        ("Аренда\nили ЗПИФ", "живые деньги\nс имущества"),
        ("Физическое\nзолото", "страховка\nот сюрпризов"),
        ("Короткий\nзапас", "чёрный день,\nне кровля"),
    ]
    for i, (a, b) in enumerate(boxes):
        x = 60 + i * 385
        dr.rounded_rectangle((x, 240, x + 350, 700), radius=20, fill=CARD)
        dr.text((x + 175, 360), a, font=font(FONT_B, 32), fill=ACCENT, anchor="ma", align="center")
        dr.text((x + 175, 520), b, font=font(FONT, 24), fill=TEXT, anchor="ma", align="center")
    footer(dr, 1600, 900, "рамка из книги · личная практика автора ≠ рекомендация")
    save(im, "02_four_baskets.png")


def fig_x25():
    im, dr = new(1600, 900)
    title(dr, "Капитал к годовому расходу")
    dr.text((48, 100), "Правило 4% — американская история; в книге — запас", font=font(FONT, 22), fill=MUTED)
    # bars as multiples
    for x, mult, lab, col, note in [
        (250, 25, "×25", CARD, "классика 4%"),
        (700, 32, "×30–35", ACCENT, "запас автора"),
    ]:
        h = int(mult * 12)
        dr.rounded_rectangle((x, 700 - h, x + 320, 700), radius=16, fill=col)
        dr.text((x + 160, 700 - h - 60), lab, font=font(FONT_B, 48), fill=TEXT, anchor="ma")
        dr.text((x + 160, 740), note, font=font(FONT, 26), fill=MUTED, anchor="ma")
    dr.text((1200, 400), "Не гарантия.\nНе закон природы.\nПоправка на чужую\nвыборку рынков.", font=font(FONT, 26), fill=TEXT, anchor="ma", align="center")
    footer(dr, 1600, 900, "Bengen / Trinity · Pfau · авторская поправка в книге")
    save(im, "02_x25_vs_x35.png")


def fig_dials():
    im, dr = new(1600, 900)
    title(dr, "Ручки А–Ж")
    dr.text((48, 100), "Когда котёл не сходится, крутят панель — не присылают извинения", font=font(FONT, 22), fill=MUTED)
    labels = [
        ("А", "возраст"),
        ("Б", "формула"),
        ("В", "приток"),
        ("Г", "окно"),
        ("Д", "техника"),
        ("Е", "номинал"),
        ("Ж", "ждать"),
    ]
    for i, (L, name) in enumerate(labels):
        x = 70 + i * 215
        dr.ellipse((x, 320, x + 160, 480), outline=ACCENT, width=4)
        dr.text((x + 80, 380), L, font=font(FONT_B, 48), fill=ACCENT, anchor="ma")
        dr.text((x + 80, 540), name, font=font(FONT_B, 24), fill=TEXT, anchor="ma")
    footer(dr, 1600, 900, "словарь автора · примеры со ссылками в статье")
    save(im, "03_dials_ag.png")


def fig_france():
    im, dr = new(1080, 1080)
    title(dr, "Франция, 2023")
    dr.text((48, 100), "Возраст подняли через ст. 49.3 Конституции", font=font(FONT, 22), fill=MUTED)
    dr.text((300, 420), "62", font=font(FONT_B, 120), fill=MUTED, anchor="ma")
    dr.text((540, 420), "→", font=font(FONT_B, 80), fill=ACCENT, anchor="ma")
    dr.text((780, 420), "64", font=font(FONT_B, 120), fill=WARN, anchor="ma")
    dr.rounded_rectangle((340, 580, 740, 700), radius=16, fill=CARD)
    dr.text((540, 620), "статья 49.3", font=font(FONT_B, 36), fill=ACCENT, anchor="ma")
    dr.text((540, 780), "без обычного голосования\nв Национальном собрании", font=font(FONT, 26), fill=MUTED, anchor="ma", align="center")
    footer(dr, 1080, 1080, "Reuters / BBC / France 24 · 2023")
    save(im, "03_france_62_64.png")


def fig_madogiwa():
    im, dr = new(1080, 1080)
    title(dr, "Японское «окно»")
    dr.text((48, 100), "madogiwa-zoku — доход есть, дела нет", font=font(FONT, 22), fill=MUTED)
    # window frame
    dr.rounded_rectangle((280, 260, 800, 700), radius=8, outline=LINE, width=8)
    dr.line((540, 260, 540, 700), fill=LINE, width=6)
    dr.line((280, 480, 800, 480), fill=LINE, width=6)
    dr.ellipse((480, 520, 600, 640), fill=CARD)  # head
    dr.rounded_rectangle((450, 640, 630, 780), radius=20, fill=CARD)  # body
    dr.text((540, 820), "серая зона между трудом и покоем", font=font(FONT, 24), fill=MUTED, anchor="ma")
    footer(dr, 1080, 1080, "Kotobank · термин madogiwa-zoku")
    save(im, "03_madogiwa.png")


def fig_tfr_world():
    im, dr = new(1600, 900)
    title(dr, "СКР: порог · Россия · Корея")
    dr.text((48, 100), "Простое воспроизводство ≈ 2,1 без миграции", font=font(FONT, 22), fill=MUTED)
    data = [("порог", 2.1, OK), ("Россия", 1.374, ACCENT), ("Корея", 0.80, WARN)]
    maxv = 2.5
    for i, (lab, val, col) in enumerate(data):
        x = 200 + i * 450
        h = int(480 * (val / maxv))
        dr.rounded_rectangle((x, 700 - h, x + 280, 700), radius=16, fill=col)
        dr.text((x + 140, 700 - h - 50), str(val).replace(".", ","), font=font(FONT_B, 40), fill=TEXT, anchor="ma")
        dr.text((x + 140, 740), lab, font=font(FONT_B, 28), fill=TEXT, anchor="ma")
    footer(dr, 1600, 900, "World Bank / Росстат / Reuters · 2025–2026")
    save(im, "04_tfr_compare.png")


def fig_cabins():
    im, dr = new(1600, 900)
    title(dr, "Каюты мира — одна боль на флаг")
    rows = [
        ("США", "середина ~95k$ · 43% без счёта"),
        ("ОЭСР", "бедность 65+ выше средней"),
        ("Корея", "СКР 0,80 после стимулов"),
        ("Россия", "СКР 1,374 · балл как цена"),
        ("Япония", "старение уже быт"),
    ]
    for i, (a, b) in enumerate(rows):
        y = 200 + i * 110
        dr.rounded_rectangle((80, y, 1520, y + 90), radius=14, fill=CARD)
        dr.text((120, y + 28), a, font=font(FONT_B, 28), fill=ACCENT)
        dr.text((400, y + 28), b, font=font(FONT, 26), fill=TEXT)
    footer(dr, 1600, 900, "сводка статьи · первоисточники внутри лонгрида")
    save(im, "04_cabins.png")


if __name__ == "__main__":
    fig_ipk()
    fig_tfr_ru()
    fig_vanguard()
    fig_oecd_poverty()
    fig_keyrate()
    fig_addendum_roof()
    fig_paygo()
    fig_formula()
    fig_moratorium()
    fig_korea()
    fig_goal()
    fig_norm()
    fig_baskets()
    fig_x25()
    fig_dials()
    fig_france()
    fig_madogiwa()
    fig_tfr_world()
    fig_cabins()
    print("DONE", len(list(OUT.glob('*.png'))), "pngs")
