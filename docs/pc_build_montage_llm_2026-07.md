# Покупка ПК для монтажа и ЛЛМ

**Дата пересчёта:** 17 июля 2026 (Москва)  
**Предыдущий разбор:** 18 июня 2026 · чат [три сборки ПК](9b8d6e21-49a2-44d6-9b74-b843e1ff3e40)  
**Инвентаризация старого ПК:** `docs/TZ_OMNI_MEDIA_EMPIRE_13.md`  
**Obsidian:** `data/obsidian_vault/Empire/покупка ПК для монтажа и ЛЛМ.md`

> **Задача:** рабочая станция под Canon R8, DaVinci/Premiere, YouTube (Pension), локальная LLM (Ollama), архив на своих HDD.  
> **Видеокарта:** RTX 4060 8 ГБ — уже есть, во все сборки.  
> **Цены:** ориентир на день документа — перед оплатой сверить наличие.  
> **Рекомендация:** Сборка 2 «Оптимум» (~134 000 ₽ без GPU).

---

## Источники (где искали раньше)

| Что | Где |
|-----|-----|
| Диалог «5 задач дома» + 3 сборки | [чат Cursor](9b8d6e21-49a2-44d6-9b74-b843e1ff3e40) |
| Железо сейчас | `docs/TZ_OMNI_MEDIA_EMPIRE_13.md` — i7-3770, DDR3, RTX 4060, диски 95–99% |
| Архитектура GPU-воркера | `docs/TZ_OMNI_MEDIA_EMPIRE_13.md` §3.A |
| Бюджет GPU в бизнес-плане | `docs/empire_business_plan_2026.md` |

---

## Что переиспользовать со старого ПК

| Компонент | Берём? | Комментарий |
|-----------|--------|-------------|
| **RTX 4060** | ✅ | Во все три сборки |
| **HDD 3.5"** | ✅ | Архив видео, не система |
| **Корпус ATX** | ⚠️ | Если GPU ≤37 см и кулер ≤165 мм — можно (экономия ~10k) |
| **БП** | ❌ | С i7-3770 обычно 10+ лет; нужен новый 650 W |
| **DDR3 / CPU / материнка** | ❌ | AM5 только DDR5 |

**Не покупаем:** видеокарту, HDD (если уже есть).

---

## Рынок на июль 2026 (важно)

1. **Ryzen 5 7600 OEM (~19 010 ₽)** сейчас **дороже** Ryzen 7 7700 (~17 980 ₽) на Regard — в Старт тоже берём **7700**.
2. **DDR5 64 ГБ** по-прежнему ~45–50% бюджета. Лучшая найденная цена: **Patriot Viper Venom 64 ГБ 6400** на CompDay — **65 184 ₽** (Kingston/Crucial kits часто 80–90k).
3. **Crucial T500 2 ТБ** на Regard — **нет в наличии**. Замена: **Kingston NV3 2 ТБ** (~22–23k).
4. **Gigabyte B650M AORUS ELITE AX** и **CC560 V2** на Regard — **нет в наличии**. Замены ниже.

**Магазины:** [Regard](https://www.regard.ru) · [CompDay](https://www.compday.ru) (м. Савёловская) · [XCOM](https://www.xcom-shop.ru) · [Citilink](https://www.citilink.ru) · [DNS](https://www.dns-shop.ru) · [Nix](https://www.nix.ru) · [e2e4](https://moscow.e2e4online.ru)

---

## База сравнения

Эталон — **Сборка 2 «Оптимум» = 100%**.  
GPU везде одна (4060) → **LLM на GPU одинаково** (~7B–8B комфортно, 13B квант, 70B нет).

---

## Сборка 1 — «Старт» (~99 000 ₽)

**Для кого:** жёсткий потолок ~100k; монтаж 1080p / лёгкий 4K; LLM с оговорками по RAM.

| Компонент | Модель | Цена | Магазин / ссылка |
|-----------|--------|------|------------------|
| CPU | AMD Ryzen 7 7700 OEM (8C/16T, 65 W) | 17 980 ₽ | [Regard](https://www.regard.ru/product/73871/processor-amd-ryzen-7-7700-oem) |
| Материнка | MSI PRO B650M-P (4×SATA, 2×M.2, 2.5G) | ~8 690 ₽ | [Citilink](https://www.citilink.ru) (поиск «PRO B650M-P») · альт. [Regard 10 110 ₽](https://www.regard.ru/product/46348/materinskaia-plata-msi-pro-b650m-p) |
| RAM | Kingston Fury Beast 32 ГБ (2×16) DDR5-5600 | 41 180 ₽ | [Regard](https://www.regard.ru/product/458078/operativnaia-pamiat-32gb-ddr5-5600mhz-kingston-fury-beast-kf556c36bbek2-32-2x16gb-kit) |
| SSD | Kingston NV3 1 ТБ M.2 | 14 000 ₽ | [Regard](https://www.regard.ru/product/699695/nakopitel-ssd-1tb-kingston-nv3-snv3s-1000g) |
| БП | MSI MAG A650BN 650 W Bronze | 4 970 ₽ | [Regard](https://www.regard.ru/product/425117/blok-pitaniia-650w-msi-mag-a650bn) |
| Кулер | DeepCool AK400 | 2 100 ₽ | [Regard](https://www.regard.ru/product/418473/kuler-deepcool-ak400) |
| Корпус | DeepCool CH560 (вместо CC560) | ~9 840 ₽ | [Nix](https://www.nix.ru/autocatalog/cases_deepcool/Miditower-Deepcool-CH560-R-CH560-BKAPE4-G-1-Black-E-ATX-bez-BP_751033.html) · или свой старый |
| **Итого** | | **~98 800 ₽** | без своего корпуса ≈ **89 000 ₽** |
| + своё | RTX 4060, HDD | 0 ₽ | |

**Минусы vs Оптимум:** 32 ГБ — swap при DaVinci + Chrome + Ollama; 1 ТБ NVMe мало под несколько 4K-проектов; Bronze БП.

---

## Сборка 2 — «Оптимум» (~134 000 ₽) ⭐ рекомендую

**Для кого:** Canon R8, DaVinci, Pension YouTube, Ollama, архив на HDD — основной сценарий.

| Компонент | Модель | Цена | Магазин / ссылка |
|-----------|--------|------|------------------|
| CPU | AMD Ryzen 7 7700 OEM | 17 980 ₽ | [Regard](https://www.regard.ru/product/73871/processor-amd-ryzen-7-7700-oem) · сверить [DNS](https://www.dns-shop.ru) / [Citilink](https://www.citilink.ru) (часто ~16.9k) |
| Материнка | MSI PRO B650M-P | ~8 690 ₽ | Citilink · [Regard](https://www.regard.ru/product/46348/materinskaia-plata-msi-pro-b650m-p) |
| RAM | **Patriot Viper Venom 64 ГБ (2×32) DDR5-6400** | **65 184 ₽** | [CompDay](https://www.compday.ru/komplektuyuszie/moduli-pamyati/358062.htm) |
| SSD | Kingston NV3 2 ТБ M.2 | ~22 300 ₽ | [e2e4](https://moscow.e2e4online.ru) · [KNS ~22 761 ₽](https://www.kns.ru/catalog/komplektuyuschie/ssd/kingston/_obem-ssd_2-tb/) |
| БП | DeepCool PN650M 650 W **Gold** (модульный) | 7 802 ₽ | [XCOM](https://www.xcom-shop.ru/deepcool_pn650m_1153204.html) |
| Кулер | DeepCool AK400 | 2 100 ₽ | [Regard](https://www.regard.ru/product/418473/kuler-deepcool-ak400) |
| Корпус | DeepCool CH560 | ~9 840 ₽ | [Nix](https://www.nix.ru/autocatalog/cases_deepcool/Miditower-Deepcool-CH560-R-CH560-BKAPE4-G-1-Black-E-ATX-bez-BP_751033.html) · или свой |
| **Итого** | | **~133 900 ₽** | без корпуса ≈ **124 000 ₽** |

**Почему эта:** 8 ядер хватает для 4K; **64 ГБ** — must для монтажа + LLM; **2 ТБ NVMe** под проекты; 4 SATA под HDD; тихий 65 W CPU; Gold БП дешевле прежнего be quiet.

**Альт. RAM (дороже):** Crucial Pro 64 ГБ 6400 — [CompDay ~88 726 ₽](https://www.compday.ru/komplektuyuszie/moduli-pamyati/585597.htm) — не брать, пока есть Patriot.

**Альт. SSD (если появится):** Crucial T500 2 ТБ — [Regard](https://www.regard.ru/product/722450/nakopitel-ssd-2tb-crucial-t500-ct2000t500ssd8) (сейчас нет в наличии).

---

## Сборка 3 — «Максимум» (~157 000 ₽)

**Для кого:** ежедневный 4K-экспорт часами, фоновый LLM, запас CPU на 3–5 лет.

| Компонент | Модель | Цена | Магазин / ссылка |
|-----------|--------|------|------------------|
| CPU | AMD Ryzen 9 7900 OEM (12C/24T) | ~32 665 ₽ | [Apltech](https://www.apltech.ru/tovar/464146/amd-ryzen-9-7900-100-000000590) · [Regard](https://www.regard.ru/product/678833/processor-amd-ryzen-9-7900-oem) |
| Материнка | Gigabyte B650 AORUS ELITE AX V2 ATX | ~14 290 ₽ | [Holodilnik](https://www.holodilnik.ru/komputernaya_tehnika/motherboards/gigabyte/b650_aorus_elite_ax_v2/) · Citilink ~14.3k |
| RAM | Patriot Viper Venom 64 ГБ | 65 184 ₽ | [CompDay](https://www.compday.ru/komplektuyuszie/moduli-pamyati/358062.htm) |
| SSD | Kingston NV3 2 ТБ | ~22 300 ₽ | e2e4 / KNS |
| БП | DeepCool PN650M Gold (или PN750D) | 7 802 ₽ | [XCOM PN650M](https://www.xcom-shop.ru/deepcool_pn650m_1153204.html) |
| Кулер | DeepCool AK620 | ~4 500 ₽ | Regard / CompDay (поиск AK620) |
| Корпус | DeepCool CH560 | ~9 840 ₽ | Nix |
| **Итого** | | **~156 600 ₽** | |

**Минусы:** +23k к Оптимуму за ~20–25% CPU; для одного монтажёра и одной 4060 выгода умеренная. Деньги лучше копить на **4060 Ti 16 ГБ** под LLM.

---

## Сравнение в процентах (эталон = Сборка 2)

| Параметр | Старт | Оптимум | Максимум |
|----------|-------|---------|----------|
| **Цена (без GPU)** | **74%** (~99k) | **100%** (~134k) | **117%** (~157k) |
| **Экспорт 4K (CPU)** | **100%** (тот же 7700) | **100%** | **125%** |
| **Монтаж + браузер + LLM (RAM)** | **50%** (32 ГБ) | **100%** (64 ГБ) | **100%** |
| **Место под проекты (NVMe)** | **50%** (1 ТБ) | **100%** (2 ТБ) | **100%** |
| **Надёжность БП** | **70%** Bronze | **95%** Gold | **95%** Gold |
| **LLM на GPU (4060 8 ГБ)** | **100%** | **100%** | **100%** |
| **Прирост vs i7-3770** | **~380%** | **~380%** | **~480%** |

---

## Корзина «купить за один день» (Оптимум)

| # | Где | Что |
|---|-----|-----|
| 1 | **CompDay** (Савёловская) | Patriot Viper 64 ГБ |
| 2 | **Regard** | Ryzen 7 7700 + AK400 (+ B650M-P, если не взяли в Citilink) |
| 3 | **Citilink** | MSI PRO B650M-P (дешевле Regard) |
| 4 | **XCOM** | DeepCool PN650M |
| 5 | **e2e4 / KNS** | Kingston NV3 2 ТБ |
| 6 | **Nix** или свой | CH560 / старый корпус |

Перед выездом: позвонить/проверить «в наличии» на сайте.

---

## Раскладка дисков

```text
M.2 NVMe          → C: Windows 11, DaVinci, Ollama, текущий проект R8
Ваш HDD #1        → E: Archive\pension\export\
Ваш HDD #2        → F: Archive\pension\raw\
rclone ночью      → Яндекс: Home-Video/
```

4K монтируйте с **NVMe**, не с HDD.

---

## После покупки

1. BIOS: EXPO/XMP для RAM (Patriot — XMP 6400).  
2. Чистая **Windows 11** + драйвер NVIDIA.  
3. DaVinci: proxy workflow для R8.  
4. Ollama: `llama3.1:8b` / `qwen2.5:7b`.  
5. Папки `Archive\pension\` + rclone.  
6. Старый i7-3770 — запасной / empire-gpu-worker, не основная станция.

---

## Рекомендация

**Берите Сборку 2 «Оптимум»** (~134k с корпусом / ~124k без).

- Сборка 1 — только при потолке **~100k**; почти наверняка потом докупите RAM до 64 ГБ (+~40–50k сейчас).  
- Сборка 3 — если монтаж **ежедневно** часами; иначе отложите разницу на GPU с 16 ГБ VRAM.  
- Отдельный NAS-мини-ПК и второй роутер под это **не нужны**.
