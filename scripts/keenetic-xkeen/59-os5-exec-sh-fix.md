# nfqws2 → 1.1.5 (без отката прошивки роутера)

## Контекст

Рабочая схема была на **nfqws2-keenetic 1.1.5** + `nfqws2-mts-unified.conf` (zapret2 0.9.x).
После обновления **nfqws2 1.2.x** (zapret2 1.0+) стратегии перестали работать на МТС.

**KeeneticOS 5.0.12 можно оставить** — откатывать прошивку роутера не обязательно.

## Симптом сейчас

- `exec sh` / `exec ash` → `Process error[268241706]: system failed [0xcffd0b2a]`
- Entware shell недоступен → `opkg install --force-downgrade` не выполнить удалённо
- USB ext4 **смонтирован** (OPKG-накопитель на месте)
- nfqws2 **1.1.5** ipk на VPS:
  `http://193.233.232.48:8787/firmware/nfqws2-keenetic_1.1.5_mipsel-3.4.ipk`

## Шаг 1 — вернуть shell (с ПК в LAN, 2 мин)

Telnet с ПК Destroy_ (`192.168.1.112`):

```
telnet 192.168.1.1
Login: admin
Password: <ваш>
exec sh
```

Если та же ошибка `system failed`:

1. Веб `https://potertiy.keenetic.pro` → **Приложения** → **OPKG**
2. Снять галку с накопителя → **Применить** → снова выбрать ext4-раздел USB → **Применить**
3. **Перезагрузка** роутера (Управление → Параметры системы)
4. Повторить `exec sh`

Альтернатива: SSH порт **222** (если пускает с LAN):

```
ssh admin@192.168.1.1 -p 222
```

## Шаг 2 — откат только nfqws2 (после shell)

Одной строкой:

```sh
curl -fsSL http://193.233.232.48:8787/60-nfqws2-downgrade-only.sh | sh
```

Или вручную:

```sh
wget -O /opt/tmp/nfqws2-downgrade.ipk \
  http://193.233.232.48:8787/firmware/nfqws2-keenetic_1.1.5_mipsel-3.4.ipk
opkg install --force-downgrade --force-reinstall /opt/tmp/nfqws2-downgrade.ipk
curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh
```

Ожидаем: `youtube=200`, `nfqueue=9`, SKeen выключен.

## Шаг 3 — веб-морда (уже сделано удалённо, проверить)

- Сетевой ускоритель (PPE) → **ВЫКЛ**
- Destroy_ / СберТелек → **без политики** Singbox
- Автообновление OS → **ВЫКЛ**
- QUIC block UDP/443 — скрипт включит сам

## Если shell так и не оживает

Тогда проблема не в версии nfqws2, а в Entware/OS 5.0 `exec` — см. `HEAL-LAN.txt` или
рассмотреть Flint 2 как отдельный шлюз обхода. **Откат OS на 4.x — крайняя мера**, не первый шаг.
