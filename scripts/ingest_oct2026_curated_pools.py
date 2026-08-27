#!/usr/bin/env python3
"""Ingest revive/stern batches + fill curated pools for autopost to Oct 2026."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

POST_RE = re.compile(
    r"^---\n(id:.*?)\n---\n(.*?)(?=^---\nid:|\Z)",
    re.M | re.S,
)


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p: Path, data: dict) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_posts(text: str) -> list[tuple[dict, str]]:
    out: list[tuple[dict, str]] = []
    for fm, body in POST_RE.findall(text):
        meta: dict[str, str] = {}
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        out.append((meta, body.strip()))
    return out


def main() -> int:
    # --- Stern batch8 ---
    stern_path = ROOT / "docs/content_factory/generated/stern_batch8_composer_2026-07-17.md"
    stern = load_json(ROOT / "data/stern_curated.json")
    existing_s = {e["id"] for e in stern["entries"]}
    added_s = 0
    for meta, body in parse_posts(stern_path.read_text(encoding="utf-8")):
        eid = meta.get("id")
        if not eid or eid in existing_s:
            continue
        if "## CHECKLIST" in body:
            body = body.split("## CHECKLIST")[0].strip()
        stern["entries"].append(
            {
                "id": eid,
                "slot": meta.get("slot", "1900"),
                "topic_raw": meta.get("topic_raw", ""),
                "body_html": body,
                "hashtags": meta.get("hashtags", "#снегири #штерн"),
                "image_prompt_en": meta.get("image_prompt_en", ""),
                "image_file": f"media/stern/topics/{eid}.jpg",
            }
        )
        existing_s.add(eid)
        added_s += 1

    stern_extra = [
        (
            "stern_0930_desk_stretch_81",
            "0930",
            "[Рутина] Плечи после ноутбука.",
            "#снегири #штерн #плечи",
            "🏛️ <b>Плечи после ноутбука</b>\n\nСидел три часа — плечи ушли вперёд.\n\nВстал, лопатки вниз и вместе. Поднял плечи к ушам и сбросил — пять раз, без рывка. Гиря подождёт.",
        ),
        (
            "stern_0930_hip_flex_82",
            "0930",
            "[Рутина] Сгибатели бедра после стула.",
            "#снегири #штерн #бёдра",
            "🏛️ <b>Стул укорачивает шаг</b>\n\nПосле дня на стуле шаг короткий, поясница ноет.\n\nВыпад лёгкий, таз вперёд. Тридцать секунд на сторону. Без шпагата в коридоре.",
        ),
        (
            "stern_0930_grip_83",
            "0930",
            "[Рутина] Кисти и предплечья.",
            "#снегири #штерн #кисти",
            "🏛️ <b>Кисти тоже устают</b>\n\nМышь держит кисть в одном угле часами.\n\nРазжал пальцы, мягкий кулак — десять раз. Покатал мячик ладонью. Потом уже гиря.",
        ),
        (
            "stern_0930_walk_84",
            "0930",
            "[Рутина] Пять минут пешком без телефона.",
            "#снегири #штерн #ходьба",
            "🏛️ <b>Пять минут без ленты</b>\n\nВышел — и сразу экран. Шея снова согнута.\n\nДо конца квартала иду без телефона. Смотрю вперёд. Тренировка без гири в кадре.",
        ),
        (
            "stern_1900_ev_078_b15",
            "1900",
            "[Офис] Перерыв между созвонами — не лента.",
            "#снегири #штерн #офис",
            "🏛️ <b>Между Zoom — не лента</b>\n\nДесять минут между созвонами я «отдыхал» в телефоне. Шея не отдыхала.\n\nВстаю, вода, два приседания у стола. Иначе день — один длинный созвон.",
        ),
        (
            "stern_1900_ev_079_b15",
            "1900",
            "[Гиря] Пауза вверху жима.",
            "#снегири #штерн #гиря",
            "🏛️ <b>Пауза важнее рывка</b>\n\nЖим без паузы вверху — махание для усталости.\n\nСекунда наверху, локоть под гирей, рёбра вниз. Вес меньше — техника чище.",
        ),
        (
            "stern_1900_ev_080_b15",
            "1900",
            "[Восстановление] Прогулка вместо «добить подход».",
            "#снегири #штерн #восстановление",
            "🏛️ <b>Иногда лучше пройтись</b>\n\nПоясница фонит — в голове «добить».\n\nОставляю гирю. Сорок минут быстрым шагом. Завтра смогу тренироваться.",
        ),
        (
            "stern_1900_ev_081_b15",
            "1900",
            "[Привычка] Одна гиря у двери.",
            "#снегири #штерн #привычка",
            "🏛️ <b>Гиря у двери</b>\n\nУбрал в шкаф — стала «на потом».\n\nСтоит у двери: выходишь — десять кубковых. Привычка на спотыкании о снаряд.",
        ),
    ]
    for eid, slot, topic, tags, body in stern_extra:
        if eid in existing_s:
            continue
        stern["entries"].append(
            {
                "id": eid,
                "slot": slot,
                "topic_raw": topic,
                "body_html": body,
                "hashtags": tags,
                "image_prompt_en": "photorealistic no face soft light",
                "image_file": f"media/stern/topics/{eid}.jpg",
            }
        )
        existing_s.add(eid)
        added_s += 1
    save_json(ROOT / "data/stern_curated.json", stern)
    print(f"stern +{added_s} total={len(stern['entries'])}")

    # --- Gdepar duo ---
    revive = (ROOT / "docs/content_factory/generated/revive_hosts_batch_2026-07-17.md").read_text(
        encoding="utf-8"
    )
    gdepar_sec = revive.split("## GDEPAR")[1].split("## LENIN")[0]
    duo = load_json(ROOT / "data/gdepar_duo_curated.json")
    existing_d = {e["id"] for e in duo["entries"]}
    added_d = 0
    for meta, body in parse_posts(gdepar_sec):
        eid = meta.get("id")
        if not eid or eid in existing_d:
            continue
        hm = re.search(r"<b>(.*?)</b>", body)
        headline = hm.group(1) if hm else eid
        pool = meta.get("pool") or "practice"
        tags = meta.get("hashtags", "#баня #гдепар")
        body_html = body if tags in body else body + "\n\n" + tags
        duo["entries"].append(
            {
                "id": eid,
                "pool": pool,
                "tag": tags.split()[-1].lstrip("#") if tags.split() else "практика",
                "headline": headline,
                "body_html": body_html,
                "hashtags": tags,
                "image_file": f"media/gdepar/topics/{eid}.jpg",
            }
        )
        existing_d.add(eid)
        added_d += 1

    duo_extra = [
        (
            "duo_aug_dry_wood_09",
            "practice",
            "дрова",
            "Дрова: сухие или нервы",
            "<b>Михалыч:</b> Сырые дрова — парная чадит, орёшь на печь.\n\n"
            "<b>Кириллыч:</b> Влажные поленья тратят жар на испарение.\n\n"
            "<b>Михалыч:</b> Колол с весны — спал спокойно зимой.",
        ),
        (
            "duo_aug_hat_10",
            "practice",
            "этикет",
            "Шапка в парной",
            "<b>Михалыч:</b> Голова без шапки на жаре — потом стучит в висках.\n\n"
            "<b>Кириллыч:</b> Войлок держит комфорт для сосудов головы.\n\n"
            "<b>Михалыч:</b> Мокрая шапка хуже сухой. Высушил — надел.",
        ),
        (
            "duo_aug_kids_11",
            "evening",
            "дети",
            "Дети и полок",
            "<b>Михалыч:</b> Ребёнка на верх сразу — лотерея, не закалка.\n\n"
            "<b>Кириллыч:</b> Нижний полок, коротко, с выходом.\n\n"
            "<b>Михалыч:</b> Геройствовать за компанию взрослых нельзя.",
        ),
        (
            "duo_aug_bastu_12",
            "practice",
            "вентиляция",
            "Басту без лекции",
            "<b>Михалыч:</b> Закрыли всё «чтоб жарче» — сидят в мешке.\n\n"
            "<b>Кириллыч:</b> Приток внизу, вытяжка выше полка.\n\n"
            "<b>Михалыч:</b> Открыл на минуту — не значит на час.",
        ),
        (
            "duo_aug_leave_13",
            "evening",
            "этикет",
            "Ушёл — оставил суше",
            "<b>Михалыч:</b> Вышел, а шайка и лужа — соседу подарок.\n\n"
            "<b>Кириллыч:</b> Протёр полок, веник убрал.\n\n"
            "<b>Михалыч:</b> Хочешь, чтоб ждали снова — начни с пола.",
        ),
        (
            "duo_aug_cold_14",
            "evening",
            "закалка",
            "Купель коротко",
            "<b>Михалыч:</b> Прыгнул на спор — губы синие.\n\n"
            "<b>Кириллыч:</b> Короткое погружение после пара — ок. Долго в ледяном — нагрузка на сердце.\n\n"
            "<b>Михалыч:</b> Вышел, отдышался — тогда второй круг.",
        ),
        (
            "duo_aug_smell_15",
            "practice",
            "печь",
            "Запах гнили vs дерева",
            "<b>Михалыч:</b> Пахнет подвалом — это не «дух бани».\n\n"
            "<b>Кириллыч:</b> Сырость в полу даёт плесень. Дерево пахнет деревом.\n\n"
            "<b>Михалыч:</b> На карте такие места в отзывах ловят быстро.",
        ),
        (
            "duo_aug_oak_birch_16",
            "practice",
            "веник",
            "Берёза утром, дуб вечером",
            "<b>Михалыч:</b> С утра берёза мягче. К вечеру — дуб, если тело приняло жар.\n\n"
            "<b>Кириллыч:</b> Дубовый лист плотнее. Новичку чаще хватает берёзы.\n\n"
            "<b>Михалыч:</b> Спорить «что круче» бессмысленно, если хлещешь как метлой.",
        ),
    ]
    for eid, pool, tag, headline, body in duo_extra:
        if eid in existing_d:
            continue
        duo["entries"].append(
            {
                "id": eid,
                "pool": pool,
                "tag": tag,
                "headline": headline,
                "body_html": f"🔥 <b>{headline}</b>\n\n{body}\n\n#баня #гдепар #{tag}",
                "hashtags": f"#баня #гдепар #{tag}",
                "image_file": f"media/gdepar/topics/{eid}.jpg",
            }
        )
        existing_d.add(eid)
        added_d += 1
    save_json(ROOT / "data/gdepar_duo_curated.json", duo)
    print(f"duo +{added_d} total={len(duo['entries'])}")

    # --- Garden ---
    garden_sec = revive.split("## GARDEN")[1] if "## GARDEN" in revive else ""
    garden_entries: list[dict] = []
    for meta, body in parse_posts(garden_sec):
        eid = meta.get("id")
        if not eid:
            continue
        hm = re.search(r"<b>(.*?)</b>", body)
        garden_entries.append(
            {
                "id": eid,
                "topic_raw": meta.get("topic_raw", f"[Степаныч] {eid}"),
                "headline": hm.group(1) if hm else eid,
                "body_html": body.split("#сад")[0].strip() if "#сад" in body else body,
                "hashtags": meta.get("hashtags", "#сад #степаныч"),
                "months": [7, 8, 9, 10],
            }
        )

    extra_g = [
        ("step_garlic_plant_09", "[Степаныч] Чеснок под зиму.", "Чеснок — пока земля копается",
         "Сажаю озимый, когда ночи холодные, а земля ещё слушается лопату. Зубок донцем вниз.\n\nМульча сверху. Не заливаю.", [9, 10]),
        ("step_cabbage_cut_10", "[Степаныч] Капуста до мороза.", "Капуста не ждёт снега",
         "Кочан плотный — срезаю с кочерыгой. Треснувший — в еду, не в подвал.", [9, 10]),
        ("step_carrot_store_11", "[Степаныч] Морковь на хранение.", "Мокрая морковь к весне каша",
         "Проветрил в тени, ботву коротко. В ящик только сухую. Мягкую убрал сразу.", [9, 10]),
        ("step_raspberry_12", "[Степаныч] Малина после сбора.", "Отплодоносившие побеги — вон",
         "Вырезаю двухлетки у земли. Оставляю сильные однолетние. Срезанное с участка.", [8, 9]),
        ("step_compost_turn_13", "[Степаныч] Компост осенью.", "Куча без воздуха — помойка",
         "Переворошил, добавил сухих листьев. Больные томаты — не в хороший компост.", [8, 9, 10]),
        ("step_cover_14", "[Степаныч] Укрывной на холод.", "Спанбонд — буфер, не грелка",
         "На дуги, не вплотную к листьям. Днём снимаю, если солнечно. Плёнка без воздуха варит.", [8, 9, 10]),
        ("step_tomato_haulm_15", "[Степаныч] Ботва больных томатов.", "Фитофтора не «сама перепрёт»",
         "Чёрные листья — с участка отдельно. Секатор протёр.", [8, 9]),
        ("step_toolshed_16", "[Степаныч] Инструмент в сарай.", "Ржавый плоскорез — весенняя злость",
         "Очистил, протёр, масло на металл. Черенки не под дождём.", [9, 10]),
        ("step_potato_sort_17", "[Степаныч] Картофель: сортировка.", "Семена и еда — разные ящики",
         "Ровные на семена отдельно. Порезанные не в погреб. Просушил в тени.", [8, 9]),
        ("step_bed_manure_18", "[Степаныч] Навоз под зиму.", "Свежий навоз весной — ожог",
         "Под пустую грядку — перепревший. Свежий в компост. Лучше недоложить.", [9, 10]),
        ("step_apple_whitewash_19", "[Степаныч] Побелка яблонь.", "Побелка от ожогов, не ритуал",
         "После листопада, сухой день. Штамб и развилки. Тонкий слой.", [10]),
        ("step_leaf_mulch_20", "[Степаныч] Листва как мульча.", "Лист с парши — не на клубнику",
         "Здоровый лист — под кусты. Больной — отдельно.", [9, 10]),
        ("step_pepper_last_21", "[Степаныч] Последний перец.", "В октябре жадность дороже",
         "Крупные снимаю. Ночью холодно — укрыл или собрал.", [9, 10]),
        ("step_water_off_22", "[Степаныч] Слить капельную.", "Лёд рвёт трубку",
         "До морозов слил ленту, промыл фильтр.", [10]),
        ("step_seed_order_23", "[Степаныч] Список семян.", "Февральский «всё подряд» — пустая трата",
         "Записываю, что повторить. Пакетики подписал годом.", [10]),
        ("step_path_weed_24", "[Степаныч] Дорожки перед зимой.", "Сорняк весной стартует раньше вас",
         "Плоскорез, мульча. Десять минут осенью экономят час в мае.", [9, 10]),
    ]
    for eid, topic, headline, body, months in extra_g:
        garden_entries.append(
            {
                "id": eid,
                "topic_raw": topic,
                "headline": headline,
                "body_html": f"🌿 <b>{headline}</b>\n\n{body}",
                "hashtags": "#сад #степаныч",
                "months": months,
            }
        )

    save_json(
        ROOT / "data/garden_curated.json",
        {"_comment": "Степаныч · Вт/Сб 12:00 · без LLM", "entries": garden_entries},
    )
    print(f"garden curated={len(garden_entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
