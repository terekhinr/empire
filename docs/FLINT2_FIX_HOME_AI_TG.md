# Flint 2 — что сломано было и как чинится

Дата: 2026-07-15

## Ответы по пунктам

### 1. Локальная сеть HOME / Samba

ПК в `192.168.1.0/24` — **LAN в порядке**. Проблема не в том, что «не в HOME», а в **обнаружении Windows**:

| Было (Keenetic) | Стало (Flint) |
|-----------------|---------------|
| Имя в сети `Keenetic`, workgroup **HOME** | Samba workgroup стоял **WORKGROUP** |
| Видно в «Сеть» | OpenWrt без wsdd часто **не видно** в обзоре |

**Исправлено:** workgroup=`HOME`, включён `wsdd2`.

**Открывать шару так (не через «Обзор»):**

```
\\192.168.1.1\download
```

Win+R → вставить → Enter → Подключить сетевой диск → `Y:` или `Z:`.

### 2. Telegram без Amnezia на ПК

Список `russia_inside` **не включает Telegram**. Нужен отдельный community list `telegram`.  
Без него Telegram шёл напрямую и резался DPI.

**Исправлено:** `podkop.main` + `telegram` → VLESS Empire `:8443`.

### 3. ИИ на ПК без Amnezia

Amnezia split через nftset **конфликтовал с FakeIP podkop** (`198.18.x.x`).  
AI-домены получали FakeIP → уходили в VLESS (не в Вену) → OpenAI/Claude/Яндекс не работали как через Amnezia на ПК.

**Исправлено правильно:** секция podkop `ai_awg`:
- `connection_type=vpn`
- `interface=awg0`
- домены из `ai-domains.txt`

### 4. Где ТЗ и что делает агент

| Документ | Содержание |
|----------|------------|
| `docs/FLINT2_SETUP.md` | миграция Keenetic → Flint |
| `docs/FLINT2_AMNEZIA.md` | Amnezia на роутере |
| `docs/REMINDERS_gdepar.md` | чеклист Empire (не сеть) |
| `scripts/flint2/` | все скрипты bootstrap |

**Скрипты фикса (на роутере / через bootstrap `:8789`):**

- `14-podkop-ai-telegram.sh` — Telegram + AI через awg0  
- `15-samba-home.sh` — Samba workgroup HOME + wsdd  

## Проверка с ПК (после фикса)

1. Telegram — открыть / отправить сообщение **без Amnezia на ПК**  
2. ChatGPT / Claude / Яндекс GPT — без Amnezia на ПК  
3. YouTube / Salut TV — как раньше  
4. `\\192.168.1.1\download` в Total Commander  

## Не делать

- Не включать Amnezia на ПК дома (конфликт с Flint).  
- Не ждать FLINT в обзоре «Сеть» — всегда IP `192.168.1.1`.  
- Не ставить nftset для AI параллельно с podkop FakeIP.
