# HA Empire — стабильный baseline

**Правило:** Teckin = прямой RTSP + `imageflip=1` на камере. **Не** go2rtc, **не** card-mod rotate для Teckin.

## Быстрая проверка

```bash
cd /root/projects/empire
venv/bin/python3 tools/ha_health_check.py
```

## Привести к baseline (после правок агента)

```bash
venv/bin/python3 tools/ha_stabilize.py --apply
```

Делает: прямой RTSP `.34`/`.84`, очищает go2rtc, flip=1, dashboard без NaN на балконе, reload интеграций.

## Камеры

| Entity | IP | Комната |
|--------|-----|---------|
| `camera.teckin_tc100` | 192.168.1.34 | Кухня |
| `camera.teckin_tc100_2` | 192.168.1.84 | Комната Макса |
| `camera.ezviz_prihozhaya` | облако | Прихожая (flip в card-mod) |
| `camera.ezviz_podezd` | облако | Подъезд |

Откат Teckin: `venv/bin/python3 tools/ha_teckin_restore_direct.py`

## Что требует физического действия

| Проблема | Действие |
|----------|----------|
| Балкон offline | Кнопка на SRW-TH01 (просыпается раз в ~5 мин) |
| Семён offline | `ha_fix_now.py --semyon-repair` + кнопка на датчике 5–10 с |
| Туалет ZHA | `ha_fix_now.py --tualet-repair` |

## Lovelace

Один блок `lovelace:` в `configuration.yaml` с `empire-dashboard` и `empire-wall`. Не дописывать второй блок.

## Чекпоинт

После стабилизации: все 4 камеры `idle`, панели в sidebar, климат без NaN.
