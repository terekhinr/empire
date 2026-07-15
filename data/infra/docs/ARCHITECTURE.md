# Архитектура Empire (2026-07)

## Домашняя сеть

```
Интернет (провайдер, CGNAT 100.64.x)
        │
   GL-MT6000 Flint 2 (OpenWrt 24.10.4)
   LAN 192.168.1.1/24  Wi‑Fi: Destroy
        │
   ├── HA (TOX1) 192.168.1.41  Tailscale 100.80.133.85
   ├── ПК, Salut TV, камеры, NAS…
   └── USB NTFS → /mnt/usb/download (Samba, Transmission)

Flint:
  podkop + sing-box  → VLESS 193.233.232.48:8443 (YouTube, Telegram, …)
  zapret2 nfqws2     → DPI-обход
  awg0 Amnezia      → 193.233.232.48:39182 (AI: Яндекс, OpenAI, Claude)
  wg0 :51820         → удалённый доступ в LAN
  reverse SSH        → VPS :6223 (админ с VPS)
```

**Keenetic:** снят с маршрутизации; настройки экспортированы в `scripts/flint2/keenetic-export.json`.

## VPS Empire

| Ресурс | Значение |
|--------|----------|
| Публичный IP | 193.233.232.48 |
| Tailscale | 100.84.19.35 (`empire-vps-ts`) |
| SSH | `ssh root@100.84.19.35` (предпочтительно) |

| Сервис | Порт | Назначение |
|--------|------|------------|
| nginx | 80/443 | neverretire.ru, gdepar.ru, hub |
| empire_webapp | 8000 | neverretire |
| empire_gdepar | 8001 | gdepar.ru |
| empire_sales | 8002 | YooKassa webhook |
| Streamlit | 8501 | dashboard |
| planning API | 8502 | tasks PWA |
| bootstrap Flint | 8789 | HTTP скрипты `scripts/flint2/` |
| VLESS Reality | 8443 | podkop с Flint |
| Amnezia AWG | 39182/udp | Docker `amnezia-awg2` |
| reverse SSH Flint | 6223 | туннель с роутера |
| HA bridge socat | 8766 | → HA Telegram |

## Облако и бэкапы

| Хранилище | Что |
|-----------|-----|
| **Яндекс.Диск** `yandex:` | VPS код, `/etc/empire`, SQLite, infra, Obsidian `obsidian (2)/Empire/` |
| **Google Drive** `gdrive:` | Obsidian, HA backup (addon на TOX1) |
| **На VPS** `/var/backups/empire/` | SQLite ежедневно |

## Секреты (не в git)

| Путь | Содержимое |
|------|------------|
| `/etc/empire/*.env` | empire, gdepar, rclone, voice, sponsr |
| `/root/.config/rclone/rclone.conf` | yandex, gdrive |
| `/root/projects/empire/.env` | ключи API (если есть) |
| Flint `/etc/amnezia/client.env` | Amnezia ключи |
| `data/infra/secrets/` | локальные копии шаблонов (на Диске в etc-empire.tar.gz) |
