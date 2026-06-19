# Home Assistant завис / «кончается место» после бэкапа

**Сервер:** armbian + HA Supervised (`192.168.1.41`, Tailscale `100.80.133.85`).

Частая причина: **диск заполнен** во время Google Drive Backup или локального снимка — Supervisor и UI «висят», перезагрузка хоста не помогает, пока место не освободили.

---

## 1. С SSH на armbian (главное)

```bash
ssh root@192.168.1.41
# или ваш пользователь
```

### Место на диске

```bash
df -h
df -i
```

Смотрите **`/``** и **`/mnt`** — если **100%** или **Use%** 95%+ — это причина.

### Что съело место (топ папок)

```bash
sudo du -xh / --max-depth=2 2>/dev/null | sort -h | tail -20
sudo du -sh /var/lib/docker/* 2>/dev/null | sort -h | tail -10
sudo du -sh /usr/share/hassio/* 2>/dev/null | sort -h | tail -10
```

### Бэкапы HA (освободить в первую очередь)

```bash
# Локальные снимки Supervisor (часто гигабайты)
sudo ls -lah /backup/ 2>/dev/null
sudo ls -lah /mnt/data/supervisor/backup/ 2>/dev/null
sudo du -sh /backup/* 2>/dev/null

# Старые — удалить ВСЕ кроме 1 последнего (если места критически мало)
# Пример (ОСТОРОЖНО — проверьте путь):
# sudo rm -f /backup/*.tar
```

Также проверьте:

```bash
sudo du -sh /config/backups 2>/dev/null
sudo journalctl --disk-usage
```

### Docker (мусор после неудачного бэкапа)

```bash
sudo docker system df
sudo docker system prune -f
# БЕЗ -a пока не уверены — не трогает volumes
```

Оставьте **минимум 2–5 ГБ** свободно на разделе с Docker.

---

## 2. Перезапуск HA (после освобождения места)

```bash
sudo docker restart homeassistant
sleep 30
sudo docker restart hassio_supervisor
```

Подождать **3–5 мин**, открыть:

- `http://192.168.1.41:8123`
- или Tailscale: `http://100.80.133.85:8123`

**Жёсткое обновление:** Ctrl+Shift+R или режим инкогнито.

---

## 3. Если UI всё ещё не открывается

```bash
sudo docker ps -a
sudo docker logs homeassistant --tail 80
sudo docker logs hassio_supervisor --tail 50
```

Ищите `No space left on device`, `OSError`, `database is locked`.

### Safe Mode (через CLI на хосте)

```bash
# HA OS / Supervised — иногда:
ha core restart
# или
docker exec homeassistant ha core restart
```

Если есть `ha` на хосте:

```bash
ha supervisor reload
ha core restart
```

---

## 4. Google Drive Backup — чтобы не повторилось

В дополнении (когда HA оживёт):

| Параметр | Значение |
|----------|----------|
| **Retain local** | **1** (не держать много копий на armbian) |
| **Retain** в облаке | 4–8 |
| **Schedule** | раз в неделю, не каждый день |

Пока место мало — **остановите** дополнение бэкапа в UI или:

```bash
docker stop addon_*google* 2>/dev/null
# имя смотрите: docker ps | grep -i backup
```

---

## 5. Проверка с другого ПК (без SSH)

С Tailscale откройте `http://100.80.133.85:8123`.

Если **API жив** (страница логина или долгая загрузка), ядро работает — проблема UI/кэш браузера или нехватка RAM.

---

## 6. Критично сохранить перед чисткой

Не удаляйте без копии:

- `/config/zigbee.db` — сеть Zigbee  
- `/config/packages/`  
- `/config/secrets.yaml`

---

## 7. Когда ничего не помогает

1. Освободить **≥3 ГБ** на диске.  
2. `docker restart homeassistant` + `hassio_supervisor`.  
3. Последний локальный `.tar` в `/backup/` — **восстановление** через Supervisor → **Backups** → Restore (если UI поднимется).

---

## Связанные файлы

- `docs/HA_GOOGLE_DRIVE_BACKUP.md`
- `docs/HA_ARMBIAN_DOCKER.md`
- `docs/HA_SUPERVISOR_INTERNET.md`
