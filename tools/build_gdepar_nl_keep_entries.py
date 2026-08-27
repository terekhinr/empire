#!/usr/bin/env python3
"""
Ingest NotebookLM keep-list → data/gdepar_book_excerpts.json

Keeps existing non-draft entries (3× Khoshev intro + any future curated).
Leaves auto_* OCR chunks marked _draft at the tail (not counted as publishable).
Appends nl_20260722_* entries from the curated batch below.

  ./venv/bin/python tools/build_gdepar_nl_keep_entries.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "gdepar_book_excerpts.json"
ID_PREFIX = "nl_20260722_"

RUBRICS = {
    "pechi_banya": {
        "title": "Печь и баня",
        "emoji": "🔥",
        "hashtag": "печь",
        "source_label": "Книга",
        "image_file": "Russian sauna stove with stones.jpg",
    },
    "istoriya_bani": {
        "title": "Из истории бани",
        "emoji": "🏛️",
        "hashtag": "история",
        "source_label": "Книга",
        "image_file": "Sanduny Moscow 2010 01.jpg",
    },
    "zdorovje_par": {
        "title": "Баня и здоровье",
        "emoji": "🩺",
        "hashtag": "здоровье",
        "source_label": "Книга",
        "image_file": "Banya Russian steam bath.jpg",
    },
    "myagkiy_par": {
        "title": "Мягкий пар",
        "emoji": "💨",
        "hashtag": "пар",
        "source_label": "Книга",
        "image_file": "Banya Russian steam bath.jpg",
    },
    "venik": {
        "title": "Веник",
        "emoji": "🌿",
        "hashtag": "веник",
        "source_label": "Книга",
        "image_file": "Banya Russian steam bath.jpg",
    },
}

HOSHEV_WORK = "«Теория бань» (2006)"
HOSHEV_AUTHOR = "Ю.М. Хошев"
BOGDANOV_WORK = "«Три века петербургской бани» (2000)"
BOGDANOV_AUTHOR = "И.А. Богданов"
VOEVODINA_WORK = "«Магия мягкой бани» (2022)"
VOEVODINA_AUTHOR = "М. Воеводина"
POLLOCK_WORK = "«Когда б не баня, все бы мы пропали» (2021)"
POLLOCK_AUTHOR = "И. Поллок"
KAMENEV_WORK = "«А.С. Залманов»"
KAMENEV_AUTHOR = "Ю.Я. Каменев"


def _e(
    slug: str,
    *,
    rubric: str,
    author: str,
    work: str,
    quote: str,
    note: str,
    host: str,
    tag: str,
    chapter: str = "",
) -> dict:
    entry = {
        "id": f"{ID_PREFIX}{slug}",
        "rubric": rubric,
        "author": author,
        "work": work,
        "quote": quote.strip(),
        "note": note.strip(),
        "host": host,
        "tag": tag,
    }
    if chapter:
        entry["chapter"] = chapter
    return entry


NEW_ENTRIES: list[dict] = [
    # ── Хошев (pechi / venik / zdorovje) ─────────────────────────────────
    _e(
        "hoshev_kamenka400",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Наиболее удачным парогенератором для бань является каменка — куча (засыпка) "
            "камней (или чугунных чушек), нагретых до высокой температуры 400–700 °С. "
            "Каменка является теплоаккумулирующим устройством, долго (часами) запасающим "
            "тепловую энергию от теплового источника относительно невысокой мощности "
            "(до 20–50 кВт) и способным затем быстро (за секунды) испарять большие количества воды."
        ),
        note="Камни — аккумулятор. Без тяжёлой кучи прозрачного пара не будет.",
        host="kirillych",
        tag="каменка",
    ),
    _e(
        "hoshev_dverca_struya",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Пар, вырывающийся из дверцы закрытой каменки, имеет форму невидимой глазом струи, "
            "которая затем смешивается с воздухом в бане. … Несмотря на малую продолжительность "
            "воздействия, паровая струя обычно ошпаривает человека, если он попадает "
            "непосредственно в зону её распространения."
        ),
        note="Не суй руки к дверце. Невидимый пар самый жгучий.",
        host="kirillych",
        tag="печь",
    ),
    _e(
        "hoshev_osushenie5",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Быстро образовавшись, повышенная влажность воздуха довольно быстро и исчезает "
            "за счёт диффузии пара на стены и конденсации на них, а также за счёт упорядоченных "
            "конвективных потоков воздуха во всей бане в целом, вызванных, в частности, "
            "нагревом воздуха печью. … время осушения воздуха не превышает 5 минут."
        ),
        note="Одной поддачи на заход не хватит — стены пьют пар.",
        host="kirillych",
        tag="влажность",
    ),
    _e(
        "hoshev_nogi_golova",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "В русских банях и саунах бывает так, что ноги вообще не прогреваются, "
            "а голова перегревается. Ясно, что подобная контрастность отнюдь не является "
            "достоинством процедуры."
        ),
        note="Пятки мёрзнут — глянь на дверь, не на печь.",
        host="kirillych",
        tag="вентиляция",
    ),
    _e(
        "hoshev_tuman_kamenka",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "…для предотвращения образования тумана необходимо повышать температуру струи пара. "
            "Именно этим руководствуются в белых банях, повышая температуру каменки."
        ),
        note="Белые клубы — камни холодноваты.",
        host="kirillych",
        tag="пар",
    ),
    _e(
        "hoshev_chernaya_dver",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "При протопке чёрной бани холодный воздух от открытой двери по полу поступает "
            "в зону очага, нагревается и в виде смеси с дымовыми газами поднимается вверх, "
            "расстилаясь по потолку, и выходит наружу через верхнюю часть двери."
        ),
        note="В чёрной всё на дверях.",
        host="kirillych",
        tag="топка",
    ),
    _e(
        "hoshev_ne_mahat",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "При протопке очага с открытыми дверями нельзя ходить по помещению, "
            "размахивая руками, поскольку возникающие при этом перемешивания воздуха "
            "(циркуляционные потоки) тотчас нарушают ламинарно текущие вдоль потолка потоки дыма, "
            "и помещение полностью задымляется."
        ),
        note="Пока топится — не мельтеши.",
        host="kirillych",
        tag="топка",
    ),
    _e(
        "hoshev_gigro_potolok",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "…влага из воздуха поглощается (конденсируется) гигроскопически внутри пор. "
            "Вследствие выделения скрытой теплоты конденсации потолок (и воздух около него) "
            "нагревается…"
        ),
        note="Дерево забирает лишнюю влагу.",
        host="kirillych",
        tag="потолок",
    ),
    _e(
        "hoshev_homoterm40",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "При достижении точки росы 40 °С (хомотермальный режим) на вёдрах, браслетах "
            "или липких плёнках, протираемых сухим полотенцем, появятся капли росы (запотевание)."
        ),
        note="Смотри на запотевание — не только на градусник.",
        host="kirillych",
        tag="режим",
    ),
    _e(
        "hoshev_mylo_glaza",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "…достаточно после мытья головы с мылом пропариться в парной и сразу же почувствовать, "
            "как начинает «есть глаза» от мыла, вымываемого потом из потовых протоков."
        ),
        note="Щиплет глаза — остатки мыла из пор выходят.",
        host="kirillych",
        tag="мытьё",
    ),
    _e(
        "hoshev_avgust",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "В определённое время выходит служитель и торжественно льёт на каменку несколько литров воды. "
            "… Такая процедура называется «сделать август»."
        ),
        note="Ведро разом — пригнись к полку.",
        host="kirillych",
        tag="поддача",
    ),
    _e(
        "hoshev_venik_opaxalo",
        rubric="venik",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Веник как опахало «зачерпывает» этот горячий воздух, располагаемый у самого потолка, "
            "и экономно направляет его именно туда, куда нужно, например, на спину человека."
        ),
        note="Жар под потолком — веником на спину.",
        host="kirillych",
        tag="веник",
    ),
    _e(
        "hoshev_venik_kw",
        rubric="venik",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "…движением веника от потолка вниз можно получить мощный импульс тепла на тело человека. "
            "Например, если скорость нисходящего потока воздуха составит величину порядка 1 м/сек, "
            "то тепловой поток на тело человека может мгновенно повыситься до 3–4 кВт/м²."
        ),
        note="Веник как поршень — плавно, не ошпарь.",
        host="kirillych",
        tag="веник",
    ),
    _e(
        "hoshev_par_gas",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Водяной же пар (водяные пары) — это не вода и не жидкость (пусть даже мелко раздробленная), "
            "а газ, это отдельные молекулы воды в пространстве…"
        ),
        note="Белые клубы — уже остывающая влага.",
        host="kirillych",
        tag="физика",
    ),
    _e(
        "hoshev_chainik",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Такая картина известна каждому по истечению пара из чайника с раскалённым над газом носиком. "
            "Если же носик чайника не перегрет и имеет температуру 100 °С и ниже, "
            "то прозрачный начальный участок струи отсутствует: «клубы пара» исходят прямо из носика."
        ),
        note="Как раскалённый носик чайника.",
        host="kirillych",
        tag="струя",
    ),
    _e(
        "hoshev_ruka_potolok",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Контроль метеоусловий обычно осуществляется помахиванием рукой у потолка, "
            "лёгкими пробными движениями веника и т. п., то есть без применения термометров "
            "и гигрометров чисто житейскими приёмами."
        ),
        note="Рука и веник скажут раньше градусника.",
        host="kirillych",
        tag="контроль",
    ),
    _e(
        "hoshev_mytie_venik",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "…окунание веника в посуду с горячей водой с встряхиванием и последующим "
            "расчёсыванием кожи ударами и скольжениями мокрого веника является не чем иным, "
            "как классическим банным приёмом мытья (водной процедурой в малом сосуде "
            "при использовании веника в качестве мочалки)."
        ),
        note="Душ без мочалки — не мытьё.",
        host="kirillych",
        tag="мытьё",
    ),
    _e(
        "hoshev_nosoglotka",
        rubric="zdorovje_par",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "А вдох воздуха в сверххомотермальном режиме (паровая баня) нагревает за счёт конденсации "
            "преимущественно именно носоглотку."
        ),
        note="Нос печёт — конденсация на слизистой.",
        host="kirillych",
        tag="дыхание",
    ),
    _e(
        "hoshev_teterinsk",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Измерения в Тетеринских банях показали повышение температуры стен и потолков… "
            "Парилка 49 88–74 82–72 44–40 Мыльная 35 44–34 39–36 38–35 Раздевалка 28 32–29 31–27 22–27"
        ),
        note="Рабочий жар под потолком.",
        host="kirillych",
        tag="температура",
    ),
    _e(
        "hoshev_struya_zony",
        rubric="pechi_banya",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Образовавшаяся струя прозрачного пара объёмом 1–2 м³ поднимается преимущественно вверх "
            "и, смешиваясь с воздухом, достигает потолка. … "
            "4 — рассеивающийся туман (дымка), 5 — зона испарившегося тумана (увлажнённый воздух)."
        ),
        note="Прозрачное — потом клубы, потом дымка.",
        host="kirillych",
        tag="струя",
    ),
    _e(
        "hoshev_dukhota",
        rubric="zdorovje_par",
        author=HOSHEV_AUTHOR,
        work=HOSHEV_WORK,
        quote=(
            "Духота — это недомогание от недостатка кислорода в крови, в том числе "
            "и из-за перегрева лёгких."
        ),
        note="Душно — не «мало пара», а перегрев и воздух.",
        host="kirillych",
        tag="дыхание",
    ),
    # ── Воеводина ───────────────────────────────────────────────────────────
    _e(
        "voevodina_provetrit",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Между заходами в парную лучше выпивать по полстакана или даже по целому стакану "
            "тёплого напитка. … нам важно прогреться … и изнутри, чтобы не вызвать контраст температур."
        ),
        note="Форточка между заходами.",
        host="kirillych",
        tag="режим",
    ),
    _e(
        "voevodina_subtropiki",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Правильная баня должна быть как тёплая увлажнённая комната — такие маленькие домашние субтропики. "
            "При этом там необходимо проветривать — чтобы дышалось легко и свободно."
        ),
        note="Мягкий пар — дышится, не давишь.",
        host="mikhalych",
        tag="мягкий пар",
    ),
    _e(
        "voevodina_kipitok",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "…используйте для увлажнения поверхностей холодную воду. Если температура комфортная — горячую. "
            "Но ни в коем случае не кипяток, иначе можно обжечься."
        ),
        note="Веник в кипяток один раз — хватит.",
        host="mikhalych",
        tag="веник",
    ),
    _e(
        "voevodina_ladoshka",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "По форме различают два типа веников: «ладошка» и «метла». «Ладошка» действительно похожа "
            "на раскрытую ладонь человека, и поэтому с её помощью удобно управлять паром."
        ),
        note="Ладошка — для паровой «подушки».",
        host="mikhalych",
        tag="веник",
    ),
    _e(
        "voevodina_pirog",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "…перемешивая его над человеком. Если паровой пирог резко опустить на лежащего, "
            "можно обжечь ему кожу или доставить дискомфорт, поэтому ваши движения должны быть "
            "максимально плавными."
        ),
        note="Паровой пирог — медленно, не обрушивай.",
        host="kirillych",
        tag="веник",
    ),
    _e(
        "voevodina_nogi_vyше",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "…расстелив свои простынки, приподнять ноги выше уровня головы и накрыть голову "
            "ароматными вениками."
        ),
        note="Ноги выше — вены отдыхают.",
        host="kirillych",
        tag="полок",
    ),
    _e(
        "voevodina_komfort32",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "32–34 °C кажутся нам комфортными… При 40 °C мы чувствуем себя как под солнцем Сочи… "
            "А 50 °C, максимум 56 °C — это предел, который мы способны вынести в течение заметного времени."
        ),
        note="Комфорт и предел — разные цифры.",
        host="kirillych",
        tag="температура",
    ),
    _e(
        "voevodina_list_polumokry",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "…листья должны быть живые, не сухие. В идеале они должны быть полумокрыми, "
            "полусухими, чуть пятнистыми."
        ),
        note="Лист полумокрый — не «капуста».",
        host="mikhalych",
        tag="веник",
    ),
    _e(
        "voevodina_venik_srok",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Лёгких плоских веников обычно хватает на один-два похода в баню, изредка — на три. "
            "Летние же веники из свежей листвы чаще всего используют единожды."
        ),
        note="Срок жизни веника — считай походы.",
        host="mikhalych",
        tag="веник",
    ),
    _e(
        "voevodina_deti",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Бабушка никогда не заставляла меня сидеть там подольше, залезать повыше, терпеть. "
            "…И с детьми, конечно же, стоит поступать так же."
        ),
        note="Детей не держать «до последнего».",
        host="mikhalych",
        tag="семья",
    ),
    _e(
        "voevodina_udary_vdol",
        rubric="venik",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "…удары осуществляются вдоль мышц, не перпендикулярно им… "
            "Воздействие на мышцы должно быть преимущественно не поперечное, а продольное."
        ),
        note="Вдоль мышцы — не поперёк.",
        host="kirillych",
        tag="веник",
    ),
    _e(
        "voevodina_peretop",
        rubric="pechi_banya",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Если баня перетоплена — вы поймёте это по тому, что полки и стены обжигающе горячие — "
            "используйте для увлажнения поверхностей холодную воду."
        ),
        note="Перетоп — холодная вода на стены, не на камни.",
        host="mikhalych",
        tag="печь",
    ),
    _e(
        "voevodina_kondensat_pot",
        rubric="myagkiy_par",
        author=VOEVODINA_AUTHOR,
        work=VOEVODINA_WORK,
        quote=(
            "Сначала наше тело ещё холодное, и на нас равномерно оседает влага, которую мы часто "
            "принимаем за первый пот. Конденсат постепенно начинает испаряться… "
            "Только потом мы начинаем постепенно прогреваться, и на нашем теле выступает пот."
        ),
        note="Мокрое на коже сначала — конденсат, не пот.",
        host="kirillych",
        tag="пар",
    ),
    # ── Богданов ────────────────────────────────────────────────────────────
    _e(
        "bogdanov_nalog1704",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "В 1704 году им был издан указ о введении во всех городах и уездах денежного сбора "
            "с каждой торговой (то есть общественной) и домовой бани. … Был составлен "
            "«Устав о банном сборе» с тринадцатью статьями."
        ),
        note="Баня в казну — ещё при Петре.",
        host="mikhalych",
        tag="налог",
    ),
    _e(
        "bogdanov_syuzor",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…в XIX веке — П. Ю. Сюзор… Известный в XIX столетии архитектор Л. Л. Бонштедт "
            "был удостоен в 1847 году звания академика за проект «роскошных» бань."
        ),
        note="Питерские бани — не сарай с угла.",
        host="kirillych",
        tag="архитектура",
    ),
    _e(
        "bogdanov_bereza_veselka",
        rubric="venik",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "Для веника старались выбрать берёзу-весёлку — с длинными, тонкими, гибкими, "
            "одетыми в густой лист ветвями; листья у неё мягкие, нежные, держатся крепко, "
            "к телу не прилипают."
        ),
        note="Весёлка — гибкая, лист держится.",
        host="mikhalych",
        tag="веник",
    ),
    _e(
        "bogdanov_shalyapin_venik",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "«Вот она, моя любимая Пушкарская баня!» — говорил Шаляпин… "
            "«…зажав в руках большущую мочалку и огромный берёзовый веник… "
            "быстро уходил к банному залу…»"
        ),
        note="Шаляпин — с веником, не с телефоном.",
        host="mikhalych",
        tag="история",
    ),
    _e(
        "bogdanov_vlaznya",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "«Влазни» продолжали жить и в тех местах, где появлялись «мыльни»; "
            "в некоторых российских деревнях они существуют и поныне."
        ),
        note="Влазня в печи — не только легенда.",
        host="kirillych",
        tag="история",
    ),
    _e(
        "bogdanov_nevesta",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…непременно топили баню, и невеста мылась вместе с подругами; прежде чем отправиться в баню, "
            "ей расплетали косу и при этом пели песни."
        ),
        note="Свадебная баня — ритуал, не SPA.",
        host="mikhalych",
        tag="обычай",
    ),
    _e(
        "bogdanov_3kopeiki",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "Посещение бань I разряда стоило 3 копейки серебром, II — 8 копеек серебром, "
            "III — 15 копеек серебром, IV — 75 копеек серебром."
        ),
        note="Классы бань — по кошельку.",
        host="kirillych",
        tag="цена",
    ),
    _e(
        "bogdanov_obzhog_ushi",
        rubric="zdorovje_par",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…банщик… совершенно одетый, измеряя температуру на полке, обжёг себе уши и нос, "
            "когда там с наслаждением парился один из посетителей."
        ),
        note="На полке жарче, чем у двери.",
        host="kirillych",
        tag="пар",
    ),
    _e(
        "bogdanov_druzhka",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…дружка пошлёт к тестю… что новобрачный пошёл в баню и новобрачная ушла. "
            "…дружка в золоте поедет… с банными дарами."
        ),
        note="Свадебный дружка — связной между дворами.",
        host="mikhalych",
        tag="обычай",
    ),
    _e(
        "bogdanov_normy1879",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "29 июля 1879 года были изданы постановления… "
            "толщина стен должна быть в 2½ кирпича, высота потолков — не менее пяти аршин, "
            "рамы двойные, притом стекла непрозрачные и т. д."
        ),
        note="Нормы 1879 — про тепло и стыд.",
        host="kirillych",
        tag="строительство",
    ),
    _e(
        "bogdanov_samozvanec",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "«Дмитрий Самозванец, — писал Н. М. Карамзин, — никогда не ходил в баню: "
            "жители московские заключили из того, что он не Русский!»"
        ),
        note="Баня как маркер «своего».",
        host="mikhalych",
        tag="история",
    ),
    _e(
        "bogdanov_chay_toska",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…в дореволюционной русской бане пили чай «до первой тоски», то есть до тех пор, "
            "пока не становилось ясно, что процесс наслаждения кончился…"
        ),
        note="Чай после парной — до «тоски», не до кофеина.",
        host="mikhalych",
        tag="обычай",
    ),
    _e(
        "bogdanov_gigant",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "На её месте стоит новый гигант социалистического быта — первая в СССР баня «Гигант». "
            "…Козлов… рассматривает своё отражение в большом зеркале."
        ),
        note="«Гигант» — про фойе, не про камни.",
        host="kirillych",
        tag="история",
    ),
    _e(
        "bogdanov_novosivkov",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "На Новосивковской улице (д. 21) до 1920-х годов стояла баня; "
            "большевики её снесли, а новую так и не поставили."
        ),
        note="Снесли — и пустырь вместо пара.",
        host="kirillych",
        tag="Петербург",
    ),
    _e(
        "bogdanov_matisov_sobaki",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…дорогой возле Матисовских бань вырвавшись, из рук ушла» — объявление о борзой, "
            "сбежавшей у бань на Мойке."
        ),
        note="У бань — и собаки, и объявления.",
        host="mikhalych",
        tag="Петербург",
    ),
    _e(
        "bogdanov_med_kovshi",
        rubric="pechi_banya",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…наливали медными лужёными ковшами… щёлок держали в медных лужёных тазах. "
            "Квас… держали в больших берестяных туесах."
        ),
        note="Медь и береста — быт старой мыльни.",
        host="kirillych",
        tag="быт",
    ),
    _e(
        "bogdanov_kostomarov",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "«Русские вообще ходили в баню очень часто; она была первою потребностью в домашней жизни, "
            "как для чистоплотности, так и для какого-то наслаждения.»"
        ),
        note="Часто — норма, не праздник.",
        host="mikhalych",
        tag="история",
        chapter="по Н.И. Костомарову",
    ),
    _e(
        "bogdanov_chernaya_topka",
        rubric="pechi_banya",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "Трубы не было, поэтому при топке дым шёл прямо в баню… "
            "Как только баня жарко натапливалась… окна и двери затворялись. "
            "На каменку вслед за тем выливалось несколько шаек воды, отчего помещение наполнялось паром."
        ),
        note="Сначала дым и проветр, потом вода.",
        host="kirillych",
        tag="топка",
    ),
    _e(
        "bogdanov_stirka",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…чернорабочие и солдаты стирали бельё, тогда как разрешалось это делать "
            "в то время только солдатам."
        ),
        note="Трёхкопеечная — ещё и прачечная.",
        host="kirillych",
        tag="история",
    ),
    _e(
        "bogdanov_kazach_banya",
        rubric="istoriya_bani",
        author=BOGDANOV_AUTHOR,
        work=BOGDANOV_WORK,
        quote=(
            "…ещё одна бадерская баня, в Московской части, в Казачьем переулке, "
            "и держал её отставной подлекарь Иван Грудинский."
        ),
        note="Казачий переулок — баня с историей.",
        host="kirillych",
        tag="Петербург",
    ),
    # ── Поллок ────────────────────────────────────────────────────────────
    _e(
        "pollock_shapp",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "…о её достоинствах и опасностях спорили Шапп д’Отрош и Антонио Санчес. "
            "Высокомерный француз Шапп беспощадно высмеивал русские банные обычаи, "
            "хотя и ворчливо признавал, что паровая баня может оказывать некоторое целебное воздействие."
        ),
        note="Шапп — один пост про «варварство» мытья.",
        host="kirillych",
        tag="история",
    ),
    _e(
        "pollock_varvary_myt",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "…северян из Новгорода, которые мылись, подобно норвежцам, в тесных срубах, "
            "а не в просторных общественных зданиях…"
        ),
        note="«Варварское» мытьё — для летописца-поляка.",
        host="mikhalych",
        tag="история",
    ),
    _e(
        "pollock_blockada",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "Во время длившейся почти 900 дней блокады Ленинграда бани служили мощным оружием "
            "в борьбе за выживание, особенно с приходом весенних оттепелей, которые пробуждали паразитов… "
            "ленинградцы выстраивались в длинные и плотные очереди к немногочисленным открытым городским баням."
        ),
        note="Блокада — очередь к бане, не к параду.",
        host="mikhalych",
        tag="блокада",
    ),
    _e(
        "pollock_dym_banniy_den",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "Раз в неделю, в «банный день», из тысяч труб валил дым, "
            "а значит, старая добрая баня не вышла из обихода."
        ),
        note="Дым над крышами — банный день жив.",
        host="mikhalych",
        tag="история",
    ),
    _e(
        "pollock_eltsin_banya",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "…дед… учинил ему напоследок собственный «экзамен», заявив: "
            "«Я тебя не пущу в строители, если ты сам, своими руками, что-нибудь не построишь. "
            "А построишь ты мне баньку…»"
        ),
        note="Экзамен деда — построить баню самому.",
        host="kirillych",
        tag="история",
    ),
    _e(
        "pollock_sanduny_nomera",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "…состоятельные горожане, заплатив больше, могли уединиться в отдельных номерах — "
            "с кожаными диванами и личными прислужниками."
        ),
        note="Семейный номер — не общий зал.",
        host="mikhalych",
        tag="Сандуны",
    ),
    _e(
        "pollock_ciryulniki",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "В профессиональные сообщества банщиков входили цирюльники, которые стригли людей, "
            "срезали мозоли и проводили простейшие лечебные процедуры: ставили банки и пускали кровь."
        ),
        note="При бане — цирюльник и мозольный мастер.",
        host="mikhalych",
        tag="история",
    ),
    _e(
        "pollock_typhus_banya",
        rubric="zdorovje_par",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "…в городах и поселках приходилось опасаться сыпного тифа. "
            "Красноармейские военачальники понимали, что для здоровья солдат очень важна баня."
        ),
        note="Вш/тиф — баня как гигиена, не романтика.",
        host="mikhalych",
        tag="гигиена",
    ),
    _e(
        "pollock_terkin_sanduny",
        rubric="istoriya_bani",
        author=POLLOCK_AUTHOR,
        work=POLLOCK_WORK,
        quote=(
            "«Баня! Что там Сандуны / С остальными банями», и никому не мешает, "
            "что «Стулья графские стоят / Вдоль стены в предбаннике»."
        ),
        note="Сандуны в поэме — дом, не музей.",
        host="mikhalych",
        tag="Сандуны",
    ),
    # ── Каменев (мягко) ───────────────────────────────────────────────────
    _e(
        "kamenev_mikrocirk",
        rubric="zdorovje_par",
        author=KAMENEV_AUTHOR,
        work=KAMENEV_WORK,
        quote=(
            "…добавки вносят целебную гармонию в их микроциркуляторное русло, течение жизненных процессов "
            "в глубине тканей организма…"
        ),
        note="Про капилляры — без «лечения всего».",
        host="mikhalych",
        tag="кровь",
        chapter="по А.С. Залманову",
    ),
]


def _load_out() -> dict:
    if OUT.is_file():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"_comment": "", "rubrics": {}, "entries": []}


def _is_publishable(entry: dict) -> bool:
    if entry.get("_draft"):
        return False
    if str(entry.get("id", "")).startswith("auto_"):
        return False
    return True


def merge(data: dict) -> tuple[int, int, int]:
    existing = data.get("entries") or []
    drafts = [e for e in existing if not _is_publishable(e)]
    publishable = [e for e in existing if _is_publishable(e)]

    by_id = {e["id"]: e for e in publishable if e.get("id")}
    added = 0
    for entry in NEW_ENTRIES:
        eid = entry["id"]
        if eid in by_id:
            continue
        by_id[eid] = entry
        added += 1

    data["rubrics"] = {**RUBRICS, **(data.get("rubrics") or {})}
    # publishable first, OCR drafts at tail
    data["entries"] = list(by_id.values()) + drafts
    return added, len(by_id), len(drafts)


def main() -> int:
    data = _load_out()
    added, non_draft, draft_n = merge(data)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUT}")
    print(f"new_entries_added={added}")
    print(f"total_non_draft={non_draft}")
    print(f"draft_tail={draft_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
