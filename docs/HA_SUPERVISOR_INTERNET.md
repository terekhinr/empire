# Ошибка: «no supervisor internet connection»

Сообщение при добавлении репозитория дополнений:

```text
StoreManager.add_repository blocked from execution, no supervisor internet connection
```

**Суть:** контейнер **Supervisor** не выходит в интернет (GitHub, магазин дополнений). HA в браузере может работать, а **Дополнения** — нет.

---

## Быстрая проверка (SSH armbian)

```bash
# 1) Интернет на хосте
ping -c 2 8.8.8.8
ping -c 2 github.com

# 2) Имя контейнера Supervisor (часто hassio_supervisor)
docker ps --format "{{.Names}}" | grep -i supervisor

# 3) Интернет из Supervisor
docker exec hassio_supervisor ping -c 2 8.8.8.8
docker exec hassio_supervisor ping -c 2 github.com
```

| Результат | Значение |
|-----------|----------|
| Хост ✅, Supervisor ❌ | DNS/сеть Docker — шаги 2–4 |
| Оба ❌ | роутер, кабель, DNS на armbian |
| Оба ✅ | перезагрузка Supervisor — шаг 5 |

---

## Шаг 1. DNS в Home Assistant (UI)

1. **Настройки** → **Система** → **Сеть** (Network).
2. Выберите активный интерфейс (часто `end0`, `eth0`, `wlan0`).
3. **IPv4** → при необходимости **Статический** или автоматический, но явно:
   - DNS: `8.8.8.8`, `1.1.1.1`
4. **Сохранить** → перезагрузка HA (**Настройки → Система → Перезагрузить**).

Повторить добавление репозитория:
`https://github.com/sabeechen/hassio-google-drive-backup`

---

## Шаг 2. DNS для Docker (armbian)

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "dns": ["8.8.8.8", "1.1.1.1"]
}
EOF
sudo systemctl restart docker
```

Подождать 1–2 мин, затем:

```bash
docker restart hassio_supervisor
# если есть:
docker restart homeassistant
```

Снова проверить `docker exec hassio_supervisor ping -c 2 github.com`.

---

## Шаг 3. Перезагрузка Supervisor

В HA (если есть **Настройки → Дополнения → Supervisor**):

- **Перезагрузить** Supervisor  
или по SSH:

```bash
docker restart hassio_supervisor
```

Через 2 мин: **Настройки → Система → Обновления** — статус Supervisor **healthy**.

---

## Шаг 4. CLI `ha` (если установлен на хосте)

```bash
ha supervisor reload
ha supervisor info
ha jobs info
```

В `ha supervisor info` смотрите `healthy: true` и отсутствие ошибок сети.

---

## Шаг 5. Время и сертификаты

```bash
timedatectl
```

Если время сильно неверное — HTTPS к GitHub ломается:

```bash
sudo timedatectl set-ntp true
```

---

## Шаг 6. Фаервол / AdGuard / Pi-hole

Если на роутере или armbian **блокировка** `github.com`, `githubusercontent.com`, `version.home-assistant.io`:

- временно отключить фильтр;
- добавить в allowlist домены GitHub и Home Assistant.

---

## Обход: бэкап без дополнения Google Drive

Пока Supervisor без интернета:

1. **Настройки** → **Система** → **Резервные копии** → **Создать резервную копию**.
2. **Скачать** `.tar` на ПК.
3. Вручную загрузить в [Google Drive](https://drive.google.com).

После починки интернета — поставить дополнение по `docs/HA_GOOGLE_DRIVE_BACKUP.md`.

---

## Чеклист

- [ ] `ping github.com` с armbian — ok  
- [ ] `docker exec hassio_supervisor ping github.com` — ok  
- [ ] DNS 8.8.8.8 в HA Network и/или `/etc/docker/daemon.json`  
- [ ] `docker restart hassio_supervisor`  
- [ ] Репозиторий Google Drive Backup добавляется без ошибки  

---

## Связанные файлы

- `docs/HA_GOOGLE_DRIVE_BACKUP.md` — после починки сети  
- `docs/HA_ADDONS_RECOMMENDED.md`  
