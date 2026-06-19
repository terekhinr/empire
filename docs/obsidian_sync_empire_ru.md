# Синхронизация Obsidian ↔ Empire (docs + финансы)

**Скрипт:** `scripts/sync_empire_obsidian.py`  
**Vault:** `data/obsidian_vault/Empire/` (Яндекс.Диск на ПК)

---

## Что делает

| Режим | Результат |
|-------|-----------|
| `--docs` | Копирует `docs/*.md` → `Empire/_canon/` (галочки `- [x]` сохраняются) |
| `--finance` | Генерирует `Empire/_finance/00-СВОДКА.md` из ledger, KPI, sales.db |
| `--all` | Оба (по умолчанию) |

**Не трогает:** `pension/gdepar/.../queue/` — постинг как раньше.

---

## Когда запускать

| Событие | Команда |
|---------|---------|
| После правок в git `docs/` | `--docs` |
| Воскресенье после KPI в дашборде | `--finance` или `--all` |
| Перед push vault с VPS | `obsidian_vps_publish.sh` (уже включает sync) |

```bash
cd /root/projects/empire
./venv/bin/python scripts/sync_empire_obsidian.py --all
```

---

## Где смотреть в Obsidian

| Путь | |
|------|--|
| `Empire/00-СЕГОДНЯ.md` | День |
| `Empire/_canon/` | ТЗ, мастер-план, матрицы — **отмечайте чеклисты** |
| `Empire/_finance/00-СВОДКА.md` | Расходы, доходы, KPI, mermaid |
| `Empire/_scenarios/` | Краткие трекеры (не перезаписываются sync) |

---

## Источники данных (финансы)

| Файл | |
|------|--|
| `data/empire_finance_ledger.json` | Расходы/доходы |
| `data/empire_weekly_kpi.json` | KPI недели (дашборд) |
| `data/pension_weekly_metrics.json` | Pension |
| `sales.db` | Оплаты |

Дашборд **P&L · Финансы** пишет в те же JSON — затем `--finance` обновляет Obsidian.

---

## Постинг

```bash
export OBSIDIAN_EMPIRE_INCOMING=/root/projects/empire/data/obsidian_vault/Empire
./venv/bin/python scripts/import_obsidian_queue.py
```

Только `*/queue/*.md` со `status: ready`.
