"""Коды регионов бань для парсеров OSM / Яндекс / форс-отзывов.

EUROPE_RU — европейская часть РФ до Урала (без Свердловской, Челябинской, Тюменской, Курган, ХМАО, ЯНАО).
URAL / SIB / FAR_EAST / RU_ALL — расширение на восток; OSM пишет только draft, сайт не трогает.
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
    # ── Урал ──
    "SVE": ("RU-SVE", "Свердловская область"),
    "CHE": ("RU-CHE", "Челябинская область"),
    "TYU": ("RU-TYU", "Тюменская область"),
    "KGN": ("RU-KGN", "Курганская область"),
    "KHM": ("RU-KHM", "Ханты-Мансийский АО — Югра"),
    "YAN": ("RU-YAN", "Ямало-Ненецкий АО"),
    # ── Сибирь ──
    "NOV": ("RU-NVS", "Новосибирская область"),
    "OMS": ("RU-OMS", "Омская область"),
    "TOM": ("RU-TOM", "Томская область"),
    "KEM": ("RU-KEM", "Кемеровская область"),
    "AL": ("RU-AL", "Республика Алтай"),
    "ALT": ("RU-ALT", "Алтайский край"),
    "KYA": ("RU-KYA", "Красноярский край"),
    "IRK": ("RU-IRK", "Иркутская область"),
    "BU": ("RU-BU", "Республика Бурятия"),
    "ZAB": ("RU-ZAB", "Забайкальский край"),
    "TY": ("RU-TY", "Республика Тыва"),
    "KK": ("RU-KK", "Республика Хакасия"),
    # ── Дальний Восток ──
    "PRI": ("RU-PRI", "Приморский край"),
    "KHA": ("RU-KHA", "Хабаровский край"),
    "AMU": ("RU-AMU", "Амурская область"),
    "SAK": ("RU-SAK", "Сахалинская область"),
    "YEV": ("RU-YEV", "Еврейская АО"),
    "MAG": ("RU-MAG", "Магаданская область"),
    "CHU": ("RU-CHU", "Чукотский АО"),
    "KAM": ("RU-KAM", "Камчатский край"),
    "SA": ("RU-SA", "Республика Саха (Якутия)"),
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

URAL_REGION_CODES: tuple[str, ...] = (
    "SVE", "CHE", "TYU", "KGN", "KHM", "YAN",
)

SIB_REGION_CODES: tuple[str, ...] = (
    "NOV", "OMS", "TOM", "KEM", "AL", "ALT", "KYA", "IRK", "BU", "ZAB", "TY", "KK",
)

FAR_EAST_REGION_CODES: tuple[str, ...] = (
    "PRI", "KHA", "AMU", "SAK", "YEV", "MAG", "CHU", "KAM", "SA",
)

# Европейская РФ до Урала (без URAL)
EUROPE_RU_REGION_CODES: tuple[str, ...] = (
    NW_REGION_CODES
    + CFO_REGION_CODES
    + VOLGA_REGION_CODES
    + SOUTH_REGION_CODES
    + CAUCASUS_REGION_CODES
)

# Вся РФ в реестре (OSM draft → enrich → pubauto; на карту только published)
RU_ALL_REGION_CODES: tuple[str, ...] = (
    EUROPE_RU_REGION_CODES
    + URAL_REGION_CODES
    + SIB_REGION_CODES
    + FAR_EAST_REGION_CODES
)

GDEPAR_REVIEW_REGIONS: tuple[str, ...] = CFO_REGION_CODES + ("SPB", "LO")

# Альтернативные ISO3166-2 для area= в Overpass (первый успешный с объектами).
# Крым/Севастополь в OSM чаще под UA-*; Курск иногда без area по RU-KUR.
REGION_AREA_ISOS: dict[str, tuple[str, ...]] = {
    "KUR": ("RU-KUR",),
    "CR": ("RU-CR", "UA-43"),
    "SEV": ("RU-SEV", "UA-40"),
}

# Запасной поиск area по name+admin_level=4, если ISO area пустая.
REGION_AREA_NAME: dict[str, str] = {
    "KUR": "Курская область",
    "CR": "Республика Крым",
    "SEV": "Севастополь",
}

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
    "SVE": "Екатеринбург",
    "CHE": "Челябинск",
    "TYU": "Тюмень",
    "KGN": "Курган",
    "KHM": "Ханты-Мансийск",
    "YAN": "Салехард",
    "NOV": "Новосибирск",
    "OMS": "Омск",
    "TOM": "Томск",
    "KEM": "Кемерово",
    "AL": "Горно-Алтайск",
    "ALT": "Барнаул",
    "KYA": "Красноярск",
    "IRK": "Иркутск",
    "BU": "Улан-Удэ",
    "ZAB": "Чита",
    "TY": "Кызыл",
    "KK": "Абакан",
    "PRI": "Владивосток",
    "KHA": "Хабаровск",
    "AMU": "Благовещенск",
    "SAK": "Южно-Сахалинск",
    "YEV": "Биробиджан",
    "MAG": "Магадан",
    "CHU": "Анадырь",
    "KAM": "Петропавловск-Камчатский",
    "SA": "Якутск",
}


def expand_region_tokens(tokens: list[str]) -> list[str]:
    """CFO, NW, VOLGA, SOUTH, CAUCASUS, URAL, SIB, FAR_EAST, EUROPE_RU, RU_ALL, GDEPAR → коды."""
    aliases = {
        "CFO": CFO_REGION_CODES,
        "NW": NW_REGION_CODES,
        "VOLGA": VOLGA_REGION_CODES,
        "SOUTH": SOUTH_REGION_CODES,
        "CAUCASUS": CAUCASUS_REGION_CODES,
        "URAL": URAL_REGION_CODES,
        "SIB": SIB_REGION_CODES,
        "FAR_EAST": FAR_EAST_REGION_CODES,
        "EAST": FAR_EAST_REGION_CODES,
        "EUROPE_RU": EUROPE_RU_REGION_CODES,
        "RU_ALL": RU_ALL_REGION_CODES,
        "FULL_RU": RU_ALL_REGION_CODES,
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
