"""Коды регионов бань для парсеров OSM / Яндекс / форс-отзывов.

EUROPE_RU — европейская часть РФ до Урала (без Свердловской, Челябинской, Тюменской, Курган, ХМАО, ЯНАО).
"""

from __future__ import annotations

# ISO 3166-2 → (код ISO, подпись для лога)
REGIONS: dict[str, tuple[str, str]] = {
    # ── Северо-Запад ──
    "SPB": ("RU-SPE", "Санкт-Петербург"),
    "LO": ("RU-LEN", "Ленинградская область"),
    "KGD": ("RU-KGD", "Калининградская область"),
    "PSK": ("RU-PSK", "Псковская область"),
    "NGR": ("RU-NGR", "Новгородская область"),
    "ARK": ("RU-ARK", "Архангельская область"),
    "VLG": ("RU-VLG", "Вологодская область"),
    "MUR": ("RU-MUR", "Мурманская область"),
    "KAR": ("RU-KR", "Республика Карелия"),
    "NEN": ("RU-NEN", "Ненецкий АО"),
    # ── Центральный ФО ──
    "MSK": ("RU-MOW", "Москва"),
    "MO": ("RU-MOS", "Московская область"),
    "BEL": ("RU-BEL", "Белгородская область"),
    "BRY": ("RU-BRY", "Брянская область"),
    "VLA": ("RU-VLA", "Владимирская область"),
    "VOR": ("RU-VOR", "Воронежская область"),
    "IVA": ("RU-IVA", "Ивановская область"),
    "KLU": ("RU-KLU", "Калужская область"),
    "KOS": ("RU-KOS", "Костромская область"),
    "KUR": ("RU-KUR", "Курская область"),
    "LIP": ("RU-LIP", "Липецкая область"),
    "ORL": ("RU-ORL", "Орловская область"),
    "RYA": ("RU-RYA", "Рязанская область"),
    "SMO": ("RU-SMO", "Смоленская область"),
    "TAM": ("RU-TAM", "Тамбовская область"),
    "TVE": ("RU-TVE", "Тверская область"),
    "TUL": ("RU-TUL", "Тульская область"),
    "YAR": ("RU-YAR", "Ярославская область"),
    # ── Приволжский ФО (до Урала) ──
    "NIZ": ("RU-NIZ", "Нижегородская область"),
    "ME": ("RU-ME", "Республика Марий Эл"),
    "CU": ("RU-CU", "Чувашская Республика"),
    "TA": ("RU-TA", "Республика Татарстан"),
    "UD": ("RU-UD", "Удмуртская Республика"),
    "PER": ("RU-PER", "Пермский край"),
    "KIR": ("RU-KIR", "Кировская область"),
    "SAM": ("RU-SAM", "Самарская область"),
    "ORE": ("RU-ORE", "Оренбургская область"),
    "PNZ": ("RU-PNZ", "Пензенская область"),
    "SAR": ("RU-SAR", "Саратовская область"),
    "ULY": ("RU-ULY", "Ульяновская область"),
    "BA": ("RU-BA", "Республика Башкортостан"),
    "MRD": ("RU-MO", "Республика Мордовия"),
    # ── Южный ФО ──
    "AD": ("RU-AD", "Республика Адыгея"),
    "AST": ("RU-AST", "Астраханская область"),
    "VGG": ("RU-VGG", "Волгоградская область"),
    "KDA": ("RU-KDA", "Краснодарский край"),
    "KLM": ("RU-KL", "Республика Калмыкия"),
    "ROS": ("RU-ROS", "Ростовская область"),
    "CR": ("RU-CR", "Республика Крым"),
    "SEV": ("RU-SEV", "Севастополь"),
    # ── Северо-Кавказский ФО ──
    "DA": ("RU-DA", "Республика Дагестан"),
    "ING": ("RU-IN", "Республика Ингушетия"),
    "KB": ("RU-KB", "Кабардино-Балкарская Республика"),
    "KC": ("RU-KC", "Карачаево-Черкесская Республика"),
    "STA": ("RU-STA", "Ставропольский край"),
    "CE": ("RU-CE", "Чеченская Республика"),
}

CFO_REGION_CODES: tuple[str, ...] = (
    "BEL", "BRY", "VLA", "VOR", "IVA", "KLU", "KOS", "KUR", "LIP",
    "MO", "MSK", "ORL", "RYA", "SMO", "TAM", "TVE", "TUL", "YAR",
)

NW_REGION_CODES: tuple[str, ...] = (
    "SPB", "LO", "KGD", "PSK", "NGR", "ARK", "VLG", "MUR", "KAR", "NEN",
)

VOLGA_REGION_CODES: tuple[str, ...] = (
    "NIZ", "ME", "CU", "TA", "UD", "PER", "KIR", "SAM", "ORE", "PNZ",
    "SAR", "ULY", "BA", "MRD",
)

SOUTH_REGION_CODES: tuple[str, ...] = (
    "AD", "AST", "VGG", "KDA", "KLM", "ROS", "CR", "SEV",
)

CAUCASUS_REGION_CODES: tuple[str, ...] = ("DA", "ING", "KB", "KC", "STA", "CE")

# Европейская РФ до Урала (без RU-SVE, RU-CHE, RU-TYU, RU-KGN, RU-KHM, RU-YAN)
EUROPE_RU_REGION_CODES: tuple[str, ...] = (
    NW_REGION_CODES
    + CFO_REGION_CODES
    + VOLGA_REGION_CODES
    + SOUTH_REGION_CODES
    + CAUCASUS_REGION_CODES
)

GDEPAR_REVIEW_REGIONS: tuple[str, ...] = CFO_REGION_CODES + ("SPB", "LO")

REGION_FALLBACK_CITY: dict[str, str] = {
    "SPB": "Санкт-Петербург",
    "MSK": "Москва",
    "KGD": "Калининград",
    "PSK": "Псков",
    "NGR": "Великий Новгород",
    "ARK": "Архангельск",
    "VLG": "Вологда",
    "MUR": "Мурманск",
    "KAR": "Петрозаводск",
    "BEL": "Белгород",
    "BRY": "Брянск",
    "VLA": "Владимир",
    "VOR": "Воронеж",
    "IVA": "Иваново",
    "KLU": "Калуга",
    "KOS": "Кострома",
    "KUR": "Курск",
    "LIP": "Липецк",
    "ORL": "Орёл",
    "RYA": "Рязань",
    "SMO": "Смоленск",
    "TAM": "Тамбов",
    "TVE": "Тверь",
    "TUL": "Тула",
    "YAR": "Ярославль",
    "NIZ": "Нижний Новгород",
    "ME": "Йошкар-Ола",
    "CU": "Чебоксары",
    "TA": "Казань",
    "UD": "Ижевск",
    "PER": "Пермь",
    "KIR": "Киров",
    "SAM": "Самара",
    "ORE": "Оренбург",
    "PNZ": "Пенза",
    "SAR": "Саратов",
    "ULY": "Ульяновск",
    "BA": "Уфа",
    "MRD": "Саранск",
    "AD": "Майкоп",
    "AST": "Астрахань",
    "VGG": "Волгоград",
    "KDA": "Краснодар",
    "KLM": "Элиста",
    "ROS": "Ростов-на-Дону",
    "CR": "Симферополь",
    "SEV": "Севастополь",
    "DA": "Махачкала",
    "ING": "Магас",
    "KB": "Нальчик",
    "KC": "Черкесск",
    "STA": "Ставрополь",
    "CE": "Грозный",
}


def expand_region_tokens(tokens: list[str]) -> list[str]:
    """CFO, NW, VOLGA, SOUTH, CAUCASUS, EUROPE_RU, GDEPAR → коды областей."""
    aliases = {
        "CFO": CFO_REGION_CODES,
        "NW": NW_REGION_CODES,
        "VOLGA": VOLGA_REGION_CODES,
        "SOUTH": SOUTH_REGION_CODES,
        "CAUCASUS": CAUCASUS_REGION_CODES,
        "EUROPE_RU": EUROPE_RU_REGION_CODES,
        "GDEPAR": GDEPAR_REVIEW_REGIONS,
    }
    out: list[str] = []
    for t in tokens:
        u = t.strip().upper()
        if not u:
            continue
        if u in aliases:
            out.extend(aliases[u])
        else:
            out.append(u)
    seen: set[str] = set()
    uniq: list[str] = []
    for r in out:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq
