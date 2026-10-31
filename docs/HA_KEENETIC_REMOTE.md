# Home Assistant — доступ из интернета через KeenDNS

Роутер: **Keenetic**, домен **[potertiy.keenetic.pro](https://potertiy.keenetic.pro/)**  
HA в LAN: **`192.168.1.41:8123`**

## Важно про адрес

| URL | Что это |
|-----|---------|
| `https://potertiy.keenetic.pro/` | **Веб-панель роутера** (443) — не Home Assistant |
| `https://ha.potertiy.keenetic.pro` | **Home Assistant** через KeenDNS (рекомендуется) |
| `http://192.168.1.41:8123` | HA дома в Wi‑Fi |
| `http://100.80.133.85:8123` | HA через Tailscale (нужен клиент на ПК) |

Корневой домен занят Keenetic OS. HA выносится на **поддомен 4-го уровня** — так задумано в [KeenDNS](https://support.keenetic.com/starter/kn-1112/en/15882-dns-service.html) и [доступе к приложениям](https://support.keenetic.com/hero/kn-1011/en/15884-remote-access-to-home-network-resources-with-dns.html).

---

## Шаг 1. KeenDNS на роутере

1. Откройте `http://192.168.1.1` или `https://potertiy.keenetic.pro`
2. **Интернет** → **KeenDNS**
3. Режим: **Облачный доступ** (Cloud access)
4. Домен `potertiy.keenetic.pro` — активен
5. **Разрешить доступ к веб-конфигуратору из интернета** — по желанию (для самого роутера)

---

## Шаг 2. Проброс HA (4-й уровень домена)

1. **Интернет** → **Доступ из интернета** (или **KeenDNS** → **Доступ к веб-приложениям**)
2. **Добавить** правило:

| Поле | Значение |
|------|----------|
| Имя / поддомен | `ha` (получится `ha.potertiy.keenetic.pro`) |
| Устройство | armbian / `192.168.1.41` |
| Протокол | HTTP |
| Порт на устройстве | `8123` |
| Доступ из интернета | **Без ограничений** |

3. Сохранить.

Keenetic сам поднимет **HTTPS** до браузера и проксирует на HA по HTTP внутри LAN.

---

## Шаг 3. Home Assistant (уже в репозитории)

HTTP в YAML больше не используется (предупреждение HA до 2027.2).

**Настройки → Система → Сеть** — trusted proxies:

- `127.0.0.1`, `::1`
- `192.168.1.1` (роутер Keenetic)
- `100.64.0.0/10` (Tailscale)
- `172.30.32.0/23` (docker HA)

После деплоя там же:

- **URL локальный:** `http://192.168.1.41:8123`
- **URL внешний:** `https://ha.potertiy.keenetic.pro`

Перезагрузка YAML или перезапуск HA.

---

## Шаг 4. Проверка

Из мобильного интернета (Wi‑Fi выключен):

```
https://ha.potertiy.keenetic.pro
```

Должен открыться логин HA. Если «Login attempt failed» или цикл редиректов — проверьте **внешний URL** в HA и что правило KeenDNS включено.

---

## Безопасность

- Сильный пароль HA + **2FA** (Настройки → Люди)
- Не публиковать URL в открытый доступ без необходимости
- Tailscale остаётся запасным каналом для админки
- Для Алисы (Yandex Smart Home) может понадобиться стабильный **внешний HTTPS URL**

---

## Альтернатива: порт на 3-м уровне

Если поддомен `ha` недоступен в прошивке, в Keenetic можно **проброс порта** (NAT):

- Внешний: `8080` (HTTP) или `8083` (HTTPS) на `potertiy.keenetic.pro`
- Внутренний: `192.168.1.41:8123`

Пример: `http://potertiy.keenetic.pro:8080` — см. [инструкцию Keenetic](https://support.keenetic.ua/hopper/kn-3810/en/20793-remote-access-to-home-resources-via-dns-using-nat-rules.html).

Внешний URL в HA тогда с портом: `https://potertiy.keenetic.pro:8083`
