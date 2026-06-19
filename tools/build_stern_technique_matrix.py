#!/usr/bin/env python3
"""УСТАРЕЛО: матрица на Цацулине/StrongFirst.

Актуальная сборка (40 разборов, видео гиревиков, субтитры):
  ./venv/bin/python tools/stern_technique_pipeline.py

Источники: tools/stern_technique_sources.py + stern_technique_breakdowns.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "stern_technique_matrix_161_200.json"

TSATSULIN = ROOT / "data" / "stern" / (
    "Гиревой тренинг. Уникальная методика тренировки с гирями Павла Цацулина - 2015.pdf"
)
MCGILL = ROOT / "data" / "stern" / "Stuart McGill - Back Mechanic - 2017.pdf"

# display_num, slug, headline, exercise_id, pdf_key, pages, yt_primary, yt_segments
ROWS: list[dict] = [
    {
        "num": 161,
        "slug": "swing_hip_hinge",
        "headline": "Мах гирей: хип-хиндж и усилие бёдер",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [68, 69],
        "youtube": {
            "primary": {
                "url": "https://www.youtube.com/watch?v=92-xf--nx88",
                "title": "StrongFirst SFG Level I — Swing",
                "channel": "StrongFirst",
            },
            "segments": [
                {
                    "start": "0:00",
                    "end": "2:45",
                    "label": "стандарты маха",
                    "commentary": "Сравните с Цацулиным: руки — проводники, взрыв из таза. В верхней точке корпус вертикален, кисть на уровне пупка–груди.",
                }
            ],
        },
    },
    {
        "num": 162,
        "slug": "swing_towel_drill",
        "headline": "Мах на полотенце: дрилл Стефана Троя",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [68, 69, 70, 71],
        "youtube": {
            "primary": {
                "url": "https://www.youtube.com/watch?v=cKx8xE8jJZs",
                "title": "Enter the Kettlebell — Pavel Tsatsouline",
                "channel": "StrongFirst",
            },
            "segments": [
                {
                    "start": "8:30",
                    "end": "12:00",
                    "label": "дриллы маха",
                    "commentary": "Полотенце выстраивает «гиря — руки — торс» в одну линию. Ошибка видна сразу: если гиря уходит вперёд, мах идёт из плеч, а не из бёдер.",
                }
            ],
        },
    },
    {
        "num": 163,
        "slug": "swing_two_lines",
        "headline": "Две прямые линии в верхней точке маха",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [71],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Swing", "channel": "StrongFirst"},
            "segments": [{"start": "0:45", "end": "2:00", "label": "верхняя фиксация", "commentary": "Линия 1: ноги — торс — голова. Линия 2: руки — гиря. Между усилием бёдер и взлётом гири — микропауза, как удар кулаком."}],
        },
    },
    {
        "num": 164,
        "slug": "vertical_jump_swing_link",
        "headline": "Вертикальный прыжок и мах: одна механика",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [67, 68],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=FDn96TMfxbM", "title": "Kettlebell swing masterclass", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "3:00", "label": "hip power", "commentary": "Прыжок с ящика и мах — одна цепь: бёдра разгибаются первыми, корпус жёсткий проводник импульса."}],
        },
    },
    {
        "num": 165,
        "slug": "swing_relaxed_arms",
        "headline": "Расслабленные руки в махе",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [69],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Swing", "channel": "StrongFirst"},
            "segments": [{"start": "1:30", "end": "2:45", "label": "руки-проводники", "commentary": "Плечи и предплечья не тянут гирю вверх. В конечной точке движение всё ещё идёт от таза."}],
        },
    },
    {
        "num": 166,
        "slug": "swing_down_phase",
        "headline": "Фаза опускания: складка в бёдрах",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [69, 70],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Swing", "channel": "StrongFirst"},
            "segments": [{"start": "2:00", "end": "2:45", "label": "нисходящая фаза", "commentary": "Гиря падает между ног; корпус наклоняется за счёт тазобедренного сустава, спина нейтральна — как в становой из программы-минимум."}],
        },
    },
    {
        "num": 167,
        "slug": "snatch_rules",
        "headline": "Рывок гири: правила и контрольные точки",
        "exercise_id": "kettlebell_snatch",
        "pdf": "tsatsulin",
        "pages": [124, 125],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Snatch", "channel": "StrongFirst"},
            "segments": [{"start": "11:00", "end": "14:43", "label": "рывок", "commentary": "Те же точки, что у маха, но рука прямая до фиксации над головой. Мягкая ловля — без удара по предплечью."}],
        },
    },
    {
        "num": 168,
        "slug": "snatch_high_pull",
        "headline": "Высокая тяга: вход в рывок (Дилуджлио)",
        "exercise_id": "kettlebell_snatch",
        "pdf": "tsatsulin",
        "pages": [126],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=cKx8xE8jJZs", "title": "Enter the Kettlebell", "channel": "StrongFirst"},
            "segments": [{"start": "25:00", "end": "28:00", "label": "high pull", "commentary": "Локоть назад выше плеча, работают мышцы верхней части спины. «Бьёте локтем», а не сгибаете руку."}],
        },
    },
    {
        "num": 169,
        "slug": "snatch_catch",
        "headline": "Мягкая ловля гири в рывке",
        "exercise_id": "kettlebell_snatch",
        "pdf": "tsatsulin",
        "pages": [125],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Snatch", "channel": "StrongFirst"},
            "segments": [{"start": "12:30", "end": "14:00", "label": "фиксация", "commentary": "Рука на линии с головой или за ней. Запястье жёсткое, плечо в суставе — иначе гиря бьёт по предплечью."}],
        },
    },
    {
        "num": 170,
        "slug": "snatch_drop_rest",
        "headline": "Сброс и «отдых в висе»",
        "exercise_id": "kettlebell_snatch",
        "pdf": "tsatsulin",
        "pages": [125],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Snatch", "channel": "StrongFirst"},
            "segments": [{"start": "13:00", "end": "14:20", "label": "сброс", "commentary": "Опускание одним движением между ног без касания груди — база для длинных сетов и экономии предплечий (как у чемпионов гиревого спорта из блока 5)."}],
        },
    },
    {
        "num": 171,
        "slug": "long_cycle_intro",
        "headline": "Длинный цикл: толчок из рэка",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=WhcSG9Fyfr4", "title": "Kettlebell Long Cycle", "channel": "Denis Vasilev / StrongFirst"},
            "segments": [{"start": "0:00", "end": "4:00", "label": "длинный цикл", "commentary": "После программы-минимум — взятие на грудь, жим, рывок. ДЦ: каждый толчок идентичен — эталон Дениса Васильева из выпуска #145."}],
        },
    },
    {
        "num": 172,
        "slug": "clean_press_rack",
        "headline": "Взятие на грудь и жим из рэка",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Clean & Press", "channel": "StrongFirst"},
            "segments": [{"start": "6:00", "end": "9:30", "label": "clean + press", "commentary": "15 минут «практики» перед основной тренировкой — не сет на отказ, а отработка траектории."}],
        },
    },
    {
        "num": 173,
        "slug": "tgu_safe_pickup",
        "headline": "Турецкий подъём: безопасный подъём с пола",
        "exercise_id": "kettlebell_getup",
        "pdf": "tsatsulin",
        "pages": [77, 78, 79],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=0bWRPC49-KI", "title": "Turkish Get-Up Basics", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "2:47", "label": "полный TGU", "commentary": "Обе руки поднимают гирю; одна выжимает, вторая помогает. Правило: не делайте с тяжёлой гирей то, что не готовы повторить контролируемо."}],
        },
    },
    {
        "num": 174,
        "slug": "tgu_levels",
        "headline": "TGU: уровни 1–3 прогрессии",
        "exercise_id": "kettlebell_getup",
        "pdf": "tsatsulin",
        "pages": [79, 80, 81],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG TGU", "channel": "StrongFirst"},
            "segments": [{"start": "2:45", "end": "6:00", "label": "этапы", "commentary": "Уровень 1: подъём/опускание с пола. Уровень 2: прямая рука, плечо в суставе. Уровень 3: половина подъёма до локтя."}],
        },
    },
    {
        "num": 175,
        "slug": "tgu_shoulder_packed",
        "headline": "TGU: плечо в суставе и визуализация",
        "exercise_id": "kettlebell_getup",
        "pdf": "tsatsulin",
        "pages": [80],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=0bWRPC49-KI", "title": "Turkish Get-Up Basics", "channel": "StrongFirst"},
            "segments": [{"start": "0:30", "end": "2:20", "label": "плечевой пояс", "commentary": "«Источник энергии» в локте, рука удлиняется к гире и вдавливает плечо в сустав — ключ к здоровым плечам overhead."}],
        },
    },
    {
        "num": 176,
        "slug": "tgu_half_getup",
        "headline": "Половина TGU: реабилитация плеча",
        "exercise_id": "kettlebell_getup",
        "pdf": "tsatsulin",
        "pages": [81],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=0bWRPC49-KI", "title": "Turkish Get-Up Basics", "channel": "StrongFirst"},
            "segments": [{"start": "1:00", "end": "2:47", "label": "до локтя", "commentary": "Кейс физиотерапевта из книги: неполные подъёмы до опоры на локоть лечили «больные плечи» без агрессивного жима."}],
        },
    },
    {
        "num": 177,
        "slug": "halo",
        "headline": "Гало (орбита гири вокруг головы)",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=cKx8xE8jJZs", "title": "Enter the Kettlebell", "channel": "StrongFirst"},
            "segments": [{"start": "15:00", "end": "17:00", "label": "halo", "commentary": "Разминка перед программой-минимум: мобильность плеч и грудного отдела без тяжёлого overhead."}],
        },
    },
    {
        "num": 178,
        "slug": "goblet_squat_wall",
        "headline": "Присед с гирей: гоблет и «лицом к стене»",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [62, 63, 67],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG Squat", "channel": "StrongFirst"},
            "segments": [{"start": "9:30", "end": "11:00", "label": "присед", "commentary": "Присед лицом к стене учит вертикальный корпус; гоблет — безопасный старт перед махами и рывками."}],
        },
    },
    {
        "num": 179,
        "slug": "mcgill_curl_up",
        "headline": "Скручивание МакГилла (curl-up)",
        "exercise_id": "mcgill_curl_up",
        "pdf": "mcgill",
        "pages": [102, 103, 104],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=Gj5t98qZaFY", "title": "McGill curl-up", "channel": "Back Mechanic"},
            "segments": [{"start": "0:00", "end": "3:00", "label": "техника", "commentary": "Руки под поясницей, одна нога согнута — фиксирует таз. Подъём на выдохе без полного сгибания поясницы."}],
        },
    },
    {
        "num": 180,
        "slug": "mcgill_side_plank",
        "headline": "Боковая планка МакГилла",
        "exercise_id": "mcgill_side_plank",
        "pdf": "mcgill",
        "pages": [105, 106],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=K2VljzCC16g", "title": "Side plank", "channel": "Back Mechanic"},
            "segments": [{"start": "0:00", "end": "2:30", "label": "side plank", "commentary": "Антиротация кора — противоположность кручению в махах и рывках. Держать линию плеч–бёдра без провисания."}],
        },
    },
    {
        "num": 181,
        "slug": "mcgill_bird_dog",
        "headline": "Птица-собака (bird dog)",
        "exercise_id": "mcgill_bird_dog",
        "pdf": "mcgill",
        "pages": [110, 118],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=wiFNA3sqjCA", "title": "Bird dog", "channel": "Back Mechanic"},
            "segments": [{"start": "0:00", "end": "3:00", "label": "bird dog", "commentary": "Контроль кора при противоположном движении рук и ног — база перед гирей и становой."}],
        },
    },
    {
        "num": 182,
        "slug": "mcgill_big3",
        "headline": "Big-3 МакГилла: порядок и дыхание",
        "exercise_id": "mcgill_big3",
        "pdf": "mcgill",
        "pages": [110],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=Gj5t98qZaFY", "title": "Big 3 overview", "channel": "Back Mechanic"},
            "segments": [{"start": "0:00", "end": "5:00", "label": "комплекс", "commentary": "Curl-up → side plank → bird dog. Связка с рубрикой Снегирей: спина атлета дореволюционной эпохи держалась на коре, не на «пампе» пресса."}],
        },
    },
    {
        "num": 183,
        "slug": "mcgill_neutral_spine",
        "headline": "Нейтральная спина: стоя и сидя",
        "exercise_id": None,
        "pdf": "mcgill",
        "pages": [78, 79, 80],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=wiFNA3sqjCA", "title": "Posture drills", "channel": "Back Mechanic"},
            "segments": [{"start": "3:00", "end": "6:00", "label": "осанка", "commentary": "Стек вертикали: голова — грудь — таз без «chin-poking». Прямая перекличка с «двумя линиями» Цацулина в махе."}],
        },
    },
    {
        "num": 184,
        "slug": "push_up_mechanics",
        "headline": "Отжимания: корпус одной линией",
        "exercise_id": "push_up",
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=IODxDxX7oi4", "title": "Perfect Push-Up", "channel": "Calisthenicmovement"},
            "segments": [{"start": "0:00", "end": "4:00", "label": "база", "commentary": "Лопатки вдоль корпуса, пресс жёсткий — как у Засса в изометрии, только динамика."}],
        },
    },
    {
        "num": 185,
        "slug": "pull_up_scapula",
        "headline": "Подтягивания: депрессия лопатки",
        "exercise_id": "pull_up",
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=eGo4IYlbE5g", "title": "Pull-up tutorial", "channel": "FitnessFAQs"},
            "segments": [{"start": "0:00", "end": "5:00", "label": "старт", "commentary": "Сначала лопатки вниз, потом сгибание локтя — иначе плечо «висит» на связках."}],
        },
    },
    {
        "num": 186,
        "slug": "hanging_legraise",
        "headline": "Вис и подъём ног: воркаут и гири",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=Pr1ieGZ5atk", "title": "Hanging leg raise", "channel": "THENX"},
            "segments": [{"start": "0:00", "end": "3:30", "label": "кор", "commentary": "Сила хвата и антиротация — общий фундамент для длинных сетов рывка."}],
        },
    },
    {
        "num": 187,
        "slug": "dip_shoulder_safe",
        "headline": "Брусья: плечи без импинджмента",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=2z8JmcrW6tY", "title": "Dip form", "channel": "Calisthenicmovement"},
            "segments": [{"start": "0:00", "end": "4:00", "label": "углы", "commentary": "Наклон корпуса и глубина — как в жиме Саксона: угол решает нагрузку на сустав."}],
        },
    },
    {
        "num": 188,
        "slug": "deadlift_setup",
        "headline": "Становая тяга: стартовая позиция",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [25, 26, 90],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=VL5Ab0T07e4", "title": "Deadlift setup", "channel": "Alan Thrall"},
            "segments": [{"start": "0:00", "end": "5:00", "label": "setup", "commentary": "Штанга у голени, лопатки над гирей — та же нейтральная спина, что в махе и у Поддубного с 112-кг штангой."}],
        },
    },
    {
        "num": 189,
        "slug": "front_squat_depth",
        "headline": "Фронтальный присед: глубина и корпус",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=v-mQm_droHg", "title": "Front squat", "channel": "Squat University"},
            "segments": [{"start": "0:00", "end": "4:00", "label": "глубина", "commentary": "Вертикальный торс — навык из тяжёлой атлетики блока 3–4, переносимый на гоблет-присед."}],
        },
    },
    {
        "num": 190,
        "slug": "bench_press_setup",
        "headline": "Жим лёжа: лопатки и ноги",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=rT7DgCr-3pg", "title": "Bench press setup", "channel": "Jeff Nippard"},
            "segments": [{"start": "0:00", "end": "5:00", "label": "setup", "commentary": "Связь с рекордами Куренцова (#118): жим — не только грудь, а жёсткая платформа из ног и лопаток."}],
        },
    },
    {
        "num": 191,
        "slug": "power_clean",
        "headline": "Power clean: базовая механика",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=KwYJTpQc5MY", "title": "Power clean", "channel": "Catalyst Athletics"},
            "segments": [{"start": "0:00", "end": "4:30", "label": "clean", "commentary": "Взрыв бёдер → локти вверх — родственник высокой тяги в рывке гири."}],
        },
    },
    {
        "num": 192,
        "slug": "bent_press_overview",
        "headline": "Bent press: обзор техники Саксона",
        "exercise_id": None,
        "pdf": None,
        "pages": [],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=KqQMKwJbM4Q", "title": "Bent press tutorial", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "6:00", "label": "bent press", "commentary": "Дополнение к выпуску #11 Саксон и trick #264: подсед под снаряд, не жим плечом."}],
        },
    },
    {
        "num": 193,
        "slug": "power_breathing_swing",
        "headline": "Дыхание при махе и рывке",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [56, 57],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=FDn96TMfxbM", "title": "Swing breathing", "channel": "StrongFirst"},
            "segments": [{"start": "3:00", "end": "6:00", "label": "дыхание", "commentary": "Выдох на усилии, «брюшной пресс как броня» — без задержки дыхания в длинных сетах."}],
        },
    },
    {
        "num": 194,
        "slug": "kb_warmup",
        "headline": "Разминка перед гирей",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=cKx8xE8jJZs", "title": "Warm-up", "channel": "StrongFirst"},
            "segments": [{"start": "5:00", "end": "8:00", "label": "разминка", "commentary": "Присед к стене, гало, качания — 15 минут практики до основного блока."}],
        },
    },
    {
        "num": 195,
        "slug": "program_minimum",
        "headline": "Программа-минимум Цацулина",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [87, 88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=cKx8xE8jJZs", "title": "Program minimum", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "8:00", "label": "обзор", "commentary": "2×12 мин махи + бег; 2×5 мин TGU. Техника важнее количества — как у Крылова с гирями без гонки за разрядами."}],
        },
    },
    {
        "num": 196,
        "slug": "farmers_walk",
        "headline": "Прогулка фермера / с гирей",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [21, 22],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=Fkzk_Rm_yEI", "title": "Farmer walk", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "3:00", "label": "farmer", "commentary": "Хват Поддубного с 16-кг тростью — тот же принцип: статическая сила кисти и корпуса."}],
        },
    },
    {
        "num": 197,
        "slug": "tspine_mobility_overhead",
        "headline": "Мобильность грудного отдела для overhead",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [76],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=0bWRPC49-KI", "title": "T-spine for TGU", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "2:47", "label": "overhead", "commentary": "TGU как «мобильность под нагрузкой» — лучше сухой растяжки перед рывком."}],
        },
    },
    {
        "num": 198,
        "slug": "beginner_back_rounding",
        "headline": "Ошибки новичка: округление спины",
        "exercise_id": "kettlebell_swing",
        "pdf": "tsatsulin",
        "pages": [70],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "Common errors", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "2:45", "label": "ошибки", "commentary": "Полотенце и становая из программы-минимум ловят сгибание поясницы. McGill Big-3 — страховка для зала."}],
        },
    },
    {
        "num": 199,
        "slug": "session_structure",
        "headline": "Связка упражнений в одной тренировке",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [87, 88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=cKx8xE8jJZs", "title": "Session flow", "channel": "StrongFirst"},
            "segments": [{"start": "40:00", "end": "46:52", "label": "структура", "commentary": "Разминка → махи → TGU → практика рывка. Не смешивать отказ и технику в один день."}],
        },
    },
    {
        "num": 200,
        "slug": "technique_as_legacy",
        "headline": "Техника как наследие: от Поддубного к программе-минимум",
        "exercise_id": None,
        "pdf": "tsatsulin",
        "pages": [5, 87, 88],
        "youtube": {
            "primary": {"url": "https://www.youtube.com/watch?v=92-xf--nx88", "title": "SFG full standards", "channel": "StrongFirst"},
            "segments": [{"start": "0:00", "end": "14:43", "label": "итог блока", "commentary": "40 выпусков техники закрывают разрыв между биографиями (#1–160) и трюками (#262+): как именно тренировались герои рубрики."}],
        },
    },
]


def _load_pdf(path: Path):
    import fitz

    return fitz.open(path)


def _extract_pages(pdf_name: str | None, pages: list[int]) -> str:
    if not pdf_name or not pages:
        return ""
    path = TSATSULIN if pdf_name == "tsatsulin" else MCGILL if pdf_name == "mcgill" else None
    if not path or not path.exists():
        return ""
    doc = _load_pdf(path)
    chunks: list[str] = []
    for p in pages:
        if 1 <= p <= len(doc):
            raw = doc[p - 1].get_text()
            text = re.sub(r"\s+", " ", raw).strip()
            if text:
                chunks.append(text[:900])
    return " … ".join(chunks)[:2400]


def _source_line(pdf_name: str | None) -> str:
    if pdf_name == "tsatsulin":
        return "П. Цацулин, «Гиревой тренинг» (2015)"
    if pdf_name == "mcgill":
        return "Stuart McGill, Back Mechanic (2017)"
    return "видеоразбор + обобщение"


def build() -> dict:
    entries = []
    for row in ROWS:
        excerpt = _extract_pages(row.get("pdf"), row.get("pages") or [])
        yt = row["youtube"]
        entry = {
            "display_num": row["num"],
            "id": f"technique_{row['num']:03d}_{row['slug']}",
            "block": 7,
            "block_title": "Техника и упражнения (наследие в движении)",
            "kind": "technique",
            "headline": row["headline"],
            "name": row["headline"].split(":")[0].strip(),
            "exercise_id": row.get("exercise_id"),
            "tag": row["slug"][:24],
            "status": "matrix",
            "note_id_conflict": (
                f"legacy_{row['num']:03d}_* в stern_athletic_legacy.json занят биографией в очереди; "
                "при заливке ready использовать id technique_NNN_* или сдвинуть очередь."
            ),
            "rag": {
                "source": _source_line(row.get("pdf")),
                "pages": row.get("pages") or [],
                "excerpt_ru": excerpt,
                "vector_db": "vector_db/stern (общий индекс; для техники надёжнее прямой extract из PDF)",
            },
            "youtube": yt,
            "post_seed": {
                "essence": row["headline"],
                "key_cues": [s["label"] for s in yt.get("segments", [])],
                "commentary": " ".join(s.get("commentary", "") for s in yt.get("segments", [])),
            },
            "clips": [
                {
                    "segment_index": i,
                    "label": seg["label"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "source_url": yt["primary"]["url"],
                    "file": None,
                    "status": "pending",
                }
                for i, seg in enumerate(yt.get("segments", []))
            ],
        }
        entries.append(entry)
    return {
        "_comment": "Матрица техники #161–#200 для рубрики Снегири. Пересборка: tools/build_stern_technique_matrix.py",
        "rubric": "athletic_legacy",
        "display_range": [161, 200],
        "kind": "technique",
        "id_prefix": "technique_",
        "entries": entries,
    }


def main() -> None:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with_excerpt = sum(1 for e in data["entries"] if e["rag"]["excerpt_ru"])
    print(f"OK: {len(data['entries'])} entries, {with_excerpt} with PDF excerpts → {OUT}")


if __name__ == "__main__":
    main()
