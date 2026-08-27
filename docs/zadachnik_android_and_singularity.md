# Задачник: Android-виджет + идеи из SingularityApp

## APK (собрано)

Файл: `android/zadachnik/zadachnik-debug.apk` (~6.3 МБ)

```bash
scp root@VPS:/root/projects/empire/android/zadachnik/zadachnik-debug.apk .
```

Установка: разрешить «неизвестные источники» → открыть APK → войти с `PLANNING_API_TOKEN`.

Виджет: рабочий стол → Виджеты → **Задачник · 7 дней**.  
Тап по заголовку: неделя → сегодня → просрочено → входящие → когда-нибудь.  
Лонгтап иконки: новая задача / ИИ / когда-нибудь / сегодня.

---

## SingularityApp — что утащили

| Идея | Статус |
|------|--------|
| Виджет 7 дней + complete + «+» | ✅ APK |
| Фильтр папки в виджете | ✅ тап по заголовку |
| Когда-нибудь | ✅ полка + API + фильтр виджета |
| Архив vs история | ✅ статус `archived`, bulk |
| Лонгтап shortcuts | ✅ Android + PWA manifest |
| ИИ: поиск и создание | ✅ assistant API + экран + FAB |

Не в v1: голосовой виджет, канбан/Гант, виджет в шторке.

---

## ИИ-ассистент

- UI: фиолетовый FAB или меню → **ИИ-ассистент**
- API: `POST /tasks/api/planning/assistant`
- Умеет: искать, создавать (сегодня/завтра/когда-нибудь), закрывать, архивировать
- Быстрый путь: «найди …» без LLM
- Env: `ZADACHNIK_ASSISTANT_MODEL` (иначе deepseek → mistral → qwen)
