# HA через Tailscale (Companion)

Armbian не выписывает HTTPS-сертификат сам. Рабочая схема:

**телефон Tailscale → VPS (HTTPS :10000) → HA по Tailscale HTTP**

| | URL |
|--|-----|
| Дома (Wi‑Fi) | `http://192.168.1.41:8123` |
| Вне дома (Tailscale Connected) | `https://moderate-amethys.tailed4746.ts.net:10000` |

## Companion

1. Tailscale на телефоне — Connected (тот же аккаунт).
2. Companion → сервер:
   - **Внутренний:** `http://192.168.1.41:8123`
   - **Внешний:** `https://moderate-amethys.tailed4746.ts.net:10000`
3. Закрыть Companion полностью → открыть снова.

Проверка в Chrome на телефоне (с Tailscale):  
`https://moderate-amethys.tailed4746.ts.net:10000`

## Технически (VPS)

- nginx слушает только Tailscale IP `:10000`, сертификат `tailscale cert`
- proxy → `http://100.80.133.85:8123`
- обновление сертификата: timer `tailscale-ha-cert-renew.timer`

WireGuard для торрентов/роутера по-прежнему: `docs/HA_REMOTE_WG.md`
