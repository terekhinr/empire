# Amnezia на ПК (Windows) + Flint — без конфликтов

## Задачи

| Что | Как |
|-----|-----|
| YouTube, обычный браузер | **мимо** Amnezia → через Flint (podkop) |
| Яндекс.Браузер / ИИ | **через** Amnezia |
| Дома HA, роутер | локально `192.168.1.x` или WireGuard |
| Cursor → VPS | Tailscale + SSH-ключ (без пароля) |

---

## Amnezia на Windows — только режим «Приложения»

На Windows IP-сплит часто конфликтует с режимом приложений. **Оставь один режим — по приложениям.**

**Не через VPN** (в списке исключений):

- `chrome.exe`
- `chrome_proxy.exe`
- `msedge.exe` (если пользуешься Edge)
- `firefox.exe` (если есть)

**Не добавляй** в исключения:

- `browser.exe` из папки **Yandex** (`...\Yandex\YandexBrowser\Application\browser.exe`)

YouTube смотри в **Chrome** (он в исключениях). Яндекс — для ИИ через VPN.

---

## Если YouTube в Chrome всё равно не открывается

1. **Amnezia → Настройки → DNS** — включи **системный DNS** или укажи `192.168.1.1` (когда дома в Wi‑Fi Destroy).
2. В **раздельном туннелировании по сайтам** (если включено) добавь **не через VPN**:
   - `youtube.com`
   - `googlevideo.com`
   - `ytimg.com`
3. Полностью **выключи Amnezia** на 1 минуту — если YouTube заработал, виновата маршрутизация/DNS Amnezia, не Flint.
4. Приложение **YouTube** (Microsoft Store) — добавь `.exe` в исключения Amnezia.

---

## WireGuard — удалённый доступ к дому (не путать с Amnezia)

**Amnezia** — VPN на VPS/работу для ИИ.  
**WireGuard на Flint** — доступ к **дому** (`192.168.1.41` HA, `192.168.1.1` LuCI).

1. Скачай конфиг: `http://193.233.232.48:8789/wg-home-lan.conf`
2. Импорт в приложение **WireGuard** (Windows), **не** в Amnezia.
3. Включай **только вне дома** (в поездке). Дома в Wi‑Fi Destroy — WG не нужен.
4. Endpoint: `46.138.207.18:51820` (если IP провайдера сменится — обновить в конфиге).

**Не держи Amnezia + WireGuard дом одновременно** без нужды — маршруты могут пересечься. Для удалённого дома: WG. Для ИИ: Amnezia.

---

## Amnezia на роутере (Flint)

Пока **не установлена** — нужен клиентский `.conf` с приватным ключом. См. `docs/FLINT2_AMNEZIA.md`.

На роутере Amnezia **не обязательна**, если на ПК уже есть Amnezia для Яндекса.

---

## Cursor → VPS без пароля (один раз на ПК)

PowerShell:

```powershell
ssh-keygen -t ed25519 -C "cursor-pc" -f $env:USERPROFILE\.ssh\id_ed25519 -N '""'
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@100.84.19.35 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Tailscale на ПК должен быть **Connected**. Потом в Cursor: **Connect to Host → `empire-vps-ts`**.

Шаблон SSH config: `deploy/cursor_ssh_config_pc.example` → `%USERPROFILE%\.ssh\config`

Полный гайд: `docs/cursor_vps_tailscale_ru.md`
