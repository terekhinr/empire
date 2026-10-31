# HA → HAOS за ~10 часов: правда про железо + план с откатом

**Дата:** 2026-10-22  
**Хост сейчас:** Armbian на **TOX1 (Amlogic S905X3)** · `192.168.1.41` / TS `100.80.133.85` · Supervised · ZHA (CP210x) · Mosquitto · LocalTuya  

**Не трогать:** Flint VPN / podkop / awg (ИИ·YouTube·TG).

---

## Жёсткий факт (чтобы не сжечь вечер)

| Вопрос | Ответ |
|--------|--------|
| Можно ли **прямо на TOX1** поставить официальный **HAOS** вместо Armbian? | **Нет** (официально). HAOS = Pi / ODROID / Green / Yellow / **Generic x86-64**. TOX1 — TV box, не в списке. |
| Что будет, если «прошить HAOS» на eMMC TOX1? | Высокий шанс **кирпича** / нет сети / нет USB; откат = дамп eMMC с SD (часы + нервы). |
| Что официально рекомендуют при уходе с Supervised? | **HAOS на поддерживаемом железе** + restore **полного** backup. |

Поэтому за **10 часов** есть **два рабочих сценария** — не «стереть TOX1 и молиться».

---

## Сценарий S0 (рекомендуется на эти 10 ч) — стабильность БЕЗ смены ОС

**Цель:** автопочинка и протоколы живы; откат = restore одного `.tar`.

```
T+0   Полный backup Supervisor → VPS + Google Drive   ✅ c0997d9f
T+1   Watchdog core + Mosquitto/Tailscale (уже) · проверка healer ✅
T+2–6 Прогон комнат: ванна, туалет, кухня, домофон, климат, камеры ✅
T+6–8 Фикс только софт-багов; железо (Zbeacon/SRW) — кнопки/питание ✅ soft
T+8–10 Наблюдение: рестарт Mosquitto, offline датчика, digest/ha ✅ smoke
```

Статус: **CP-20261022c** — Armbian остаётся; фикс spam-скриптов + Mosquitto autoheal + healer entity.

**Откат S0:** `ha backups restore <slug>` на этом же TOX1 (Supervised остаётся).

**HAOS откладываем** до появления **второго** ящика (мини‑ПК x86 / Pi5 / ODROID) — тогда S1.

---

## Сценарий S1 — HAOS на ВТОРОМ железе (нормальная миграция + откат = старый TOX1)

Нужен любой поддерживаемый бокс (даже на время теста): mini‑PC x86, NUC, Pi4/5, ODROID.

```
TOX1 (живой прод) ──полный backup──► USB/VPS
                                      │
                                      ▼
                              Новый бокс + HAOS
                              onboarding → Restore backup
                              Zigbee stick ПЕРЕНОСИТСЯ в новый USB
                                      │
                         тест 4–8 ч (автоматики, MQTT, Alice)
                                      │
                    OK ──► IP: новый = .41 (или DHCP reservation)
                         TOX1 выключить (хранить как откат 48ч)
                    FAIL ──► stick обратно в TOX1, включить старый,
                              новый бокс выкинуть из LAN
```

**Откат S1:** физически вернуть Zigbee‑стик на TOX1, питание TOX1 ON, новый HAOS OFF. Минуты, не перепрошивка.

### Железо под HAOS (минимум)

| | Минимум | Комфорт |
|--|---------|---------|
| CPU | x86-64 или Pi4 4GB | N100 / Pi5 8GB |
| Disk | 32 GB SSD | 64–128 GB |
| RAM | 2 GB | 4+ GB |
| Сеть | Ethernet в тот же `192.168.1.0/24` | + Tailscale addon |

Образы: [Installation](https://www.home-assistant.io/installation/) → Generic x86-64 или Raspberry Pi.

---

## Сценарий S2 — «HAOS на этом же TOX1» (НЕ на 10 часов)

Только если готовы: полный дамп eMMC на PC, экспериментальный amlogic‑образ, риск потери дней.  
**Для текущего окна — отказ.**

---

## Rollback-пакет (сделать СРАЗУ, до любых экспериментов)

1. **Полный** backup HA (не partial addon):
   ```bash
   ssh root@100.80.133.85 'ha backups new --name "pre-haos-$(date +%Y%m%d-%H%M)" --homeassistant'
   ```
2. Скачать `.tar` на VPS:
   ```bash
   mkdir -p /root/backups/ha && scp root@100.80.133.85:/usr/share/hassio/backup/<file>.tar /root/backups/ha/
   ```
3. Google Drive Backup addon — «Backup now» (если аккаунт уже связан).
4. Зафиксировать: Zigbee USB `10c4:ea60`, IP `.41`, список аддонов.

Откат на TOX1 после кривого эксперимента с конфигом:

```bash
ha backups list
ha backups restore <slug>
```

---

## 10‑часовой таймбокс (если идём S0 сегодня)

| Час | Действие | Критерий «ок» |
|-----|----------|----------------|
| 0 | Full backup → VPS | файл >50MB, list видит slug |
| 0.5 | Watchdogs ON, Mosquitto boot auto | `ha apps info core_mosquitto` → watchdog true |
| 1 | `ha_health_check` + `/ha` | камеры/климат/safety OK |
| 2 | Ванная: presence on → свет; off → выкл через 3м | физика |
| 3 | Туалет HOBEIAN + домофон MQTT | звонок/открыть |
| 4 | Кухня чайник + Zbeacon кухни | |
| 5 | Прихожая: если Zbeacon offline — только питание (не YAML) | |
| 6 | Балкон SRW: кнопка датчика | t° не unknown |
| 7 | Искусственный kill Mosquitto → watchdog поднял | <2 мин |
| 8 | Рестарт HA core → MQTT/ZHA вернулись | <5 мин |
| 9–10 | Только наблюдение + запись в checkpoint | |

Если к часу 3 «всё красное» — **стоп**, restore backup, не углубляться.

---

## Автопочинка (уже канон + что добить в S0)

См. `HA_STABILITY_ARCHITECTURE.md`.

| Слой | Статус |
|------|--------|
| VPS healer + ha_watcher | есть |
| Digest / `/ha` | есть |
| Core watchdog | ON |
| Mosquitto / Tailscale watchdog | ON (2026-10-22) |
| Flint ha-healer | есть (не трогать VPN) |
| Healthchecks.io ping | опционально (`EMPIRE_HA_HC_PING_URL`) |

---

## Решение владельца (одно слово)

- **`S0`** — сегодня только стабилизация TOX1 + полный бэкап (рекомендую).  
- **`S1`** — есть второй бокс под HAOS → миграция с откатом = старый TOX1.  
- **`S2`** — не предлагаю в этом окне.

Агент: при **`S0`** сразу делает backup + прогон чеклиста. При **`S1`** — ждёт IP/доступ нового бокса, не трогает eMMC TOX1.
