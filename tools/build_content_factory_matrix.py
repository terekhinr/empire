#!/usr/bin/env python3
"""Собирает полные матрицы тем и BATCH_MANIFEST для Gemini Content Factory."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "content_factory" / "gemini_export"

# --- Gdepar: базовые темы + расширение до целевого объёма ---
GDEPAR_PRACTICE_SEEDS = [
    ("TR", "Берёзовый веник: замочить, не сварить"),
    ("TR", "Дубовый vs берёзовый — без священной войны"),
    ("TR", "Полки: низ — не «для слабаков»"),
    ("TR", "Веник в руке: ритм, не кнут"),
    ("TE", "Печь «тлеет» vs «жарит» — без термометра в руке"),
    ("TE", "Вентиляция: зачем щель"),
    ("TE", "Камни: трещина — когда страшно"),
    ("TE", "Электропечь: первый раз — что спросить"),
    ("NW", "Первый заход: три коротких"),
    ("NW", "Жар «на троечку»"),
    ("NW", "Головокружение — стоп"),
    ("NW", "Что взять в первую баню: минимум"),
    ("BT", "Очередь к ковшу"),
    ("BT", "Разговор или тишина"),
    ("BT", "Полотенце, шапка, тапки — быт"),
    ("PS", "Баня vs смартфон"),
    ("PS", "Пар без понтов"),
    ("MP", "Как читать отзыв на gdepar.ru"),
    ("MP", "Фильтр на карте: город, отопление"),
    ("MP", "Что значит «мягкий пар» в отзывах"),
    ("GN", "Вода до, во время, после"),
    ("GN", "Мёд и соль — без магии"),
]

GDEPAR_EVENING_SEEDS = [
    ("FL", "Банник в деревне — быт или байка"),
    ("FL", "Приметы: что из быта, что туризм"),
    ("BT", "Сосед по полке — бытовая сцена"),
    ("BT", "Баня с подростком — осторожность"),
    ("RC", "Квас к пару"),
    ("RC", "Иван-чай к пару"),
    ("RC", "Травяной настой — простой"),
    ("PS", "Баня вдвоём: границы"),
    ("PS", "Сон после воскресной бани"),
    ("PS", "Холодная купель: осторожность"),
    ("TR", "Привычка, не культ"),
    ("NW", "Чужой веник и правила"),
    ("GN", "Алкоголь и пар — отдельный разговор"),
    ("TE", "Электропечь vs дрова — без религии"),
    ("MP", "Язык отзывов на карте"),
    ("MP", "«На карте писали» — расшифровка"),
]

GDEPAR_BW_SEEDS = [
    ("MP", "Атмосфера и тип парилки"),
    ("NW", "Мягкий пар для новичка"),
    ("TR", "Свой веник по отзывам"),
    ("BT", "Семейная баня"),
    ("TE", "Электро vs дрова на примере"),
    ("MP", "После работы: логистика"),
    ("MP", "Сезон зима/лето в отзывах"),
    ("MP", "Тишина и режим без гаджетов"),
]

# Дополнительные углы для добора до 58/69
GDEPAR_PRACTICE_EXTRA = [
    ("TE", "Дрова берёзовые: почему не сосна «навсегда»"),
    ("TR", "Запаривание веника: пару минут, не час"),
    ("NW", "Общая баня: первый раз один"),
    ("BT", "Шумные соседи — одна граница"),
    ("PS", "Дыхание в парилке — не задерживать"),
    ("MP", "Рейтинг звёзд vs текст отзыва"),
    ("GN", "Голодный vs сытный заход"),
    ("TR", "Веник дубовый: кому плотный пар"),
    ("TE", "Зола в печи — когда чистить"),
    ("NW", "Сухой веник — ошибка новичка"),
    ("BT", "Очередь в раздевалке — этикет"),
    ("PS", "Баня после тяжёлого дня — без героизма"),
    ("MP", "Карта: загород vs город"),
    ("GN", "Травяной чай вместо пива"),
    ("TR", "Париться молча — норма, не понты"),
    ("TE", "Влажность: ковш и режим"),
    ("NW", "Верхняя полка — не в первый визит"),
    ("BT", "Свой ковш vs общий"),
    ("PS", "Отпуск от экрана на 40 минут"),
    ("MP", "Фильтр «свой веник» на карте"),
    ("GN", "Соль: щепотка, не горсть"),
    ("TR", "Пар от печи vs от камней"),
    ("TE", "Дверь в парилку: открыть или нет"),
    ("NW", "Сколько сидеть на полке — честно"),
    ("BT", "Принести своё мыло — норм"),
    ("PS", "Баня вдвоём с другом — без допроса"),
    ("MP", "Отзыв «жарко» — что уточнить"),
    ("GN", "Вода с лимоном — не религия"),
    ("TR", "Веник оак: плотнее удар"),
    ("TE", "Запах дыма — когда тревожно"),
    ("NW", "Смущение в общей бане"),
    ("BT", "Дети в бане — тишина и коротко"),
    ("PS", "Пар как пауза, не шоу"),
    ("MP", "gdepar.ru/map — с чего начать поиск"),
    ("GN", "Не есть тяжёлое за час"),
    ("TR", "Свой веник с собой — зачем"),
]

GDEPAR_EVENING_EXTRA = [
    ("FL", "Баня в пословицах — пересказ"),
    ("BT", "Сосед рассказал байку — одна сцена"),
    ("RC", "Квас домашний: кислота"),
    ("PS", "Воскресный ритуал без пафоса"),
    ("TR", "Баня как еженедельная точка"),
    ("NW", "Стыд новичка — нормален"),
    ("GN", "Пиво после — почему спорят"),
    ("TE", "Умный дом в бане — нужен ли"),
    ("MP", "Отзыв «ободрали» — красный флаг"),
    ("FL", "Банник в кино vs в жизни"),
    ("BT", "Спор о температуре у печи"),
    ("RC", "Мёд в чай после пара"),
    ("PS", "Тишина как роскошь"),
    ("TR", "Веник в подарок — этикет"),
    ("NW", "Ошибка с полотенцем"),
    ("GN", "Голод после бани"),
    ("TE", "Печь растопил не ты — как просить"),
    ("MP", "Баня «для своих» в отзывах"),
    ("FL", "Чёрт в бане — фольклор"),
    ("BT", "Жена/муж в бане — границы"),
    ("RC", "Сельдерей и зелень — не hype"),
    ("PS", "Усталость хорошая vs плохая"),
    ("TR", "Баня зимой vs летом"),
    ("NW", "Слишком долго в парилке"),
    ("GN", "Кофе до бани — осторожно"),
    ("TE", "Купель ледяная — кому нет"),
    ("MP", "Сравнить две бани на карте"),
    ("FL", "Баня в анекдоте — не инструкция"),
    ("BT", "Музыка в бане — за и против"),
    ("RC", "Уха после бани — деревня"),
    ("PS", "Одиночество в парилке"),
    ("TR", "Запах дуба и берёзы"),
    ("NW", "Паника от жара — выход"),
    ("GN", "Сухой горло после пара"),
    ("TE", "Когда звать банщика"),
    ("MP", "Премиум vs простая баня на карте"),
    ("FL", "Сонник про баню — смех"),
    ("BT", "Простуда и баня — не сегодня"),
    ("RC", "Кисель vs квас"),
    ("PS", "Баня перед важным днём"),
    ("TR", "Париться пятницей — ритм"),
    ("NW", "Сравнить с сауной"),
    ("GN", "Детокс-маркетинг — антипример"),
    ("TE", "Парогенератор — ожидания"),
    ("MP", "Написать отзыв после визита"),
    ("FL", "Баня в сказке"),
    ("BT", "Долгий разговор в предбаннике"),
    ("RC", "Настой мяты"),
    ("PS", "Баня и сон глубже"),
    ("TR", "Веник в машине — запах"),
    ("NW", "Смущение наготы"),
    ("GN", "Не мерить пульс наугад"),
    ("TE", "Трещит печь — норма?"),
    ("MP", "Баня рядом с домом на карте"),
]

STERN_RT = [
    "[Рутина] Утреннее пробуждение ЦНС.",
    "[Рутина] Суставная гимнастика.",
    "[Рутина] Вакуум и дыхание.",
    "[Рутина] Растяжка ног.",
    "[Рутина] Зарядка для шеи.",
    "[Рутина] Йога для силовиков.",
    "[Рутина] Разминка перед гирей.",
    "[Рутина] Вечерняя разгрузка спины.",
    "[Рутина] Перерыв каждые 45 минут.",
    "[Рутина] Лестница вместо лифта.",
    "[Рутина] Мобильность таза за 5 минут.",
    "[Рутина] Плечи после клавиатуры.",
    "[Рутина] Ступни и голеностоп утром.",
    "[Рутина] Дыхание 4-4 перед совещанием.",
    "[Рутина] Разгибание грудного у стены.",
]

STERN_EV = [
    "[Психология] Выгорание и дисциплина.",
    "[Психология] Маленькие рамки вместо силы воли.",
    "[Восстановление] Сон: свет, температура, кофеин.",
    "[Восстановление] Кортизол без мистики.",
    "[Срывы] Возврат в режим после срыва.",
    "[Срывы] Срыв не сжигает неделю.",
    "[Мотивация] История привычки без хайпа.",
    "[Мотивация] Цель на 4 недели.",
    "[Возрастной тренинг] После 40: разминка и объём.",
    "[Возрастной тренинг] Суставы и сила.",
    "[Ответы] Ловушки мотивации.",
    "[Ответы] Коуч vs блокнот.",
    "[Психология] Среда сильнее характера.",
    "[Восстановление] Выходной без чувства вины.",
    "[Питание] Дефицит без самобичевания.",
]


def _slug(s: str) -> str:
    import re

    s = s.lower()
    s = re.sub(r"[^\wа-яё]+", "_", s, flags=re.I)
    return s.strip("_")[:40]


def build_gdepar_pool(seeds: list, extra: list, prefix: str, target: int) -> list[dict]:
    out: list[dict] = []
    n = 1
    for dir_, headline in seeds + extra:
        if len(out) >= target:
            break
        out.append({"id": f"{prefix}-{n:03d}", "dir": dir_, "headline": headline})
        n += 1
    while len(out) < target:
        out.append(
            {
                "id": f"{prefix}-{n:03d}",
                "dir": "BT",
                "headline": f"Банный быт #{n} — уточнить в фазе 0",
            }
        )
        n += 1
    return out


def build_stern_pool(seeds: list, prefix: str, target: int) -> list[dict]:
    out = []
    for i, topic in enumerate(seeds, 1):
        if len(out) >= target:
            break
        out.append({"id": f"{prefix}-{i:03d}", "topic_raw": topic})
    # циклическое дополнение вариациями
    i = len(out) + 1
    while len(out) < target:
        base = seeds[(i - 1) % len(seeds)]
        out.append({"id": f"{prefix}-{i:03d}", "topic_raw": base.replace(".", f" (вариант {(i // len(seeds)) + 1}).")})
        i += 1
    return out


def chunk(lst: list, size: int) -> list[list]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    practice = build_gdepar_pool(GDEPAR_PRACTICE_SEEDS, GDEPAR_PRACTICE_EXTRA, "GDP-PR", 58)
    evening = build_gdepar_pool(GDEPAR_EVENING_SEEDS, GDEPAR_EVENING_EXTRA, "GDP-EV", 69)
    banya = [
        {"id": f"GDP-BW-{i:03d}", "dir": d, "headline": h}
        for i, (d, h) in enumerate(GDEPAR_BW_SEEDS, 1)
    ]
    while len(banya) < 12:
        banya.append({"id": f"GDP-BW-{len(banya)+1:03d}", "dir": "MP", "headline": "Карточка бани — факты с сайта"})

    stern_rt = build_stern_pool(STERN_RT, "STR-RT", 80)
    stern_ev = build_stern_pool(STERN_EV, "STR-EV", 69)

    matrix = {"practice": practice, "evening": evening, "banya_week": banya}
    (OUT / "gdepar_topic_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "stern_topic_matrix.json").write_text(
        json.dumps({"routine_0930": stern_rt, "evening_1900": stern_ev}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Markdown matrices
    lines = ["# Gdepar — полная матрица тем (до 15.09.2026)\n"]
    for pool, items in matrix.items():
        lines.append(f"\n## pool `{pool}` ({len(items)} тем)\n")
        lines.append("| id | dir | headline |")
        lines.append("|----|-----|----------|")
        for e in items:
            lines.append(f"| {e['id']} | {e['dir']} | {e['headline']} |")
    (OUT / "gdepar_POST_MATRIX_FULL.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Stern — полная матрица тем (до 15.09.2026)\n"]
    for pool, items in [("routine_0930", stern_rt), ("evening_1900", stern_ev)]:
        lines.append(f"\n## slot `{pool}` ({len(items)} тем)\n")
        lines.append("| id | topic_raw |")
        lines.append("|----|-----------|")
        for e in items:
            lines.append(f"| {e['id']} | {e['topic_raw']} |")
    (OUT / "stern_POST_MATRIX_FULL.md").write_text("\n".join(lines), encoding="utf-8")

    # Batch manifest
    batches = []
    bi = 1
    for pool_name, items, pool_key in [
        ("gdepar", practice, "practice"),
        ("gdepar", evening, "evening"),
        ("gdepar", banya, "banya_week"),
    ]:
        for ch in chunk(items, 12):
            ids = [x["id"] for x in ch]
            batches.append(
                {
                    "batch_id": f"{pool_name}_{bi:02d}",
                    "channel": pool_name,
                    "pool": pool_key,
                    "count": len(ids),
                    "topic_ids": ids,
                }
            )
            bi += 1
    bi = 1
    for pool_name, items, slot in [
        ("stern", stern_rt, "0930"),
        ("stern", stern_ev, "1900"),
    ]:
        for ch in chunk(items, 12):
            ids = [x["id"] for x in ch]
            batches.append(
                {
                    "batch_id": f"{pool_name}_{bi:02d}",
                    "channel": pool_name,
                    "slot": slot,
                    "count": len(ids),
                    "topic_ids": ids,
                }
            )
            bi += 1

    md = ["# BATCH_MANIFEST — генерация до 15.09.2026\n", f"Всего батчей: {len(batches)}\n"]
    md.append("| batch_id | channel | pool/slot | count | topic_ids |")
    md.append("|----------|---------|-----------|-------|-----------|")
    for b in batches:
        pool = b.get("pool") or b.get("slot")
        ids = ", ".join(b["topic_ids"])
        md.append(f"| {b['batch_id']} | {b['channel']} | {pool} | {b['count']} | {ids} |")
    (OUT / "BATCH_MANIFEST_sept2026.md").write_text("\n".join(md), encoding="utf-8")
    (OUT / "BATCH_MANIFEST_sept2026.json").write_text(
        json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK → {OUT} ({len(batches)} batches)")


if __name__ == "__main__":
    main()
