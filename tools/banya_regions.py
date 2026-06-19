"""Коды регионов бань для парсеров OSM / Яндекс / форс-отзывов."""

from __future__ import annotations

# ISO 3166-2 субъекты РФ → короткий код в banya_spots.region
REGIONS: dict[str, tuple[str, str]] = {
  # Северо-Запад (карта gdepar: Питер + ЛО)
    "SPB": ("RU-SPE", "Санкт-Петербург"),
    "LO":  ("RU-LEN", "Ленинградская область"),
  # ЦФО
    "MSK": ("RU-MOW", "Москва"),
    "MO":  ("RU-MOS", "Подмосковье (МО)"),
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
}

# Все субъекты Центрального федерального округа (18)
CFO_REGION_CODES: tuple[str, ...] = (
    "BEL", "BRY", "VLA", "VOR", "IVA", "KLU", "KOS", "KUR", "LIP",
    "MO", "MSK", "ORL", "RYA", "SMO", "TAM", "TVE", "TUL", "YAR",
)

# Регионы для залпа отзывов: ЦФО + Питер/ЛО (как на карте gdepar)
GDEPAR_REVIEW_REGIONS: tuple[str, ...] = CFO_REGION_CODES + ("SPB", "LO")

# Подстановка города, если OSM не дал addr:city
REGION_FALLBACK_CITY: dict[str, str] = {
    "SPB": "Санкт-Петербург",
    "MSK": "Москва",
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
}


def expand_region_tokens(tokens: list[str]) -> list[str]:
    """CFO → все коды ЦФО; GDEPAR → CFO + SPB + LO."""
    out: list[str] = []
    for t in tokens:
        u = t.strip().upper()
        if not u:
            continue
        if u == "CFO":
            out.extend(CFO_REGION_CODES)
        elif u == "GDEPAR":
            out.extend(GDEPAR_REVIEW_REGIONS)
        else:
            out.append(u)
    # сохраняем порядок, убираем дубли
    seen: set[str] = set()
    uniq: list[str] = []
    for r in out:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq
