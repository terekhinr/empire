# Amnezia VPN на Flint 2

## Что уже известно

| Параметр | Keenetic (экспорт) | VPS (сейчас) |
|----------|-------------------|--------------|
| Протокол | AmneziaWG 2 | Docker `amnezia-awg2` |
| Endpoint | `103.31.77.69:30315` (старый) | **`193.233.232.48:39182/udp`** |
| Client IP | `10.8.1.10/32` | уточнить в Amnezia |
| MTU | 1324 | 1324 |
| Obfuscation | Jc=4, Jmin=10, Jmax=50, S1=17, S2=129, H1–H4 | как в шаблоне |

Шаблон без секретного ключа: `scripts/flint2/amnezia-client.env.template`  
Генерация: `python3 scripts/flint2/export-amnezia-keenetic.py`

## Что нужно от вас (один из вариантов)

1. **Файл клиента** из приложения Amnezia (`.conf` / QR / «Поделиться») для роутера  
   или  
2. **Новый клиент** в Amnezia на VPS → экспорт конфига для «router-home»

Обязательные поля:

- `PrivateKey` (клиент) — **нет в экспорте Keenetic**
- `PublicKey` (сервер)
- `PresharedKey`
- `Endpoint` — `193.233.232.48:39182`
- `Address` — `10.8.1.x/32`
- AWG: Jc, Jmin, Jmax, S1, S2, H1, H2, H3, H4

## Установка на Flint

### Stock GL.iNet (до прошивки OpenWrt)

1. Admin Panel → **VPN** → **AmneziaWG 2** → Import config / QR  
2. Включить туннель, проверить `ping 10.8.0.1` или интернет через VPN

### OpenWrt 24.10 (после bootstrap)

```sh
mkdir -p /etc/amnezia
# скопировать client.env с VPS (без коммита в git!)
curl -fsSL http://193.233.232.48:8789/09-amnezia-awg.sh | sh
```

На OpenWrt может понадобиться пакет **amneziawg** / kmod с obfuscation — если `wg-quick` не понимает Jc/Jmin, используйте stock GL.iNet import или LuCI AmneziaWG.

## Проверка

```sh
wg show
ping -c2 1.1.1.1
curl -sI https://ifconfig.me
```

## ИИ через Amnezia (podkop `ai_awg`)

Список доменов: `scripts/flint2/ai-domains.txt` (Cursor, OpenAI, Claude, Gemini AI, Windsurf, OpenRouter, …).  
Применение на Flint:

```sh
curl -fsSL http://193.233.232.48:8789/36-ai-via-amnezia.sh | sh
```

YouTube / Telegram остаются в VLESS. На ПК дома Amnezia-клиент **выкл**.  
Не добавлять в список целиком `google.com` / `gstatic.com` — только узкие AI-хосты.
