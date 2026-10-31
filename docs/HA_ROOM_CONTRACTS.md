# Контракты комнат (отслеживание без спама)

**Цель:** ловить дрейф настроек и рассинхрон «датчик ↔ свет» до того, как дом «сломается» навсегда.

Проверка: `./venv/bin/python scripts/empire_ha_watcher.py --check`  
В дайджест: блок «Дом / контракты» (`empire_status_digest.py`).

## Комнаты

| Комната | Presence | Свет (template) | Raw | Sens | Timeout | Off after | День | Ночь |
|---------|----------|-----------------|-----|------|---------|-----------|------|------|
| Ванная | `sonoff_snzb_06p` | `empire_vannaya_svet` | `tz3000_mgusv51k_ts0052` | Medium | 15с | 30с | 100% | 20% 01:00–05:51 |
| Прихожая | `sonoff_snzb_06p_2` | `empire_prihozhaya_svet` | `tz3000_mgusv51k_ts0052_2` | Medium | 15с | off через 15с после clear; recover если occupancy on / свет off | 100% | 40% 01:00–05:51 |
| Туалет | `sonoff_snzb_06p_3` | `empire_tualet_svet` | `hobeian_zg_301z` | — | — | ~15с | on/off | — |

## Что считает watcher

1. **Дрейф Sonoff** — live sensitivity/timeout ≠ контракт.
2. **Desync** — presence=`off` ≥2 мин, template light=`on` (в `--check` только отчёт; heal — Flint/HA).
3. **Unavailable raw** при живом presence — в offline-список.

Не шлёт realtime TG. Только state → утро/вечер digest + `/ha`.

## Безопасный heal (канон)

| Симптом | Действие |
|---------|----------|
| Desync presence off / light on | Flint healer desync (уже) |
| Mosquitto down | addon watchdog + HA restart Mosquitto |
| Stuck occupancy >45 мин | Flint stuck-off |
| Дрейф Medium→High | выровнять при старте HA + алерт в digest |

YAML init **не** должен ставить High (ванная уже Medium).
