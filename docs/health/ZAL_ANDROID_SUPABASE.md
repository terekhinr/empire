# Зал + Supabase (постоянный синк)

Приложение работает **без** этих шагов (только офлайн). Синк нужен, чтобы данные жили в облаке и восстанавливались на новом телефоне.

## 1. Создать проект

1. Зайти на [supabase.com](https://supabase.com) → New project.
2. Дождаться готовности БД.

## 2. SQL

В **SQL Editor** вставить и выполнить файл:

`android/zal/supabase/schema.sql`

## 3. Ключи

Project Settings → API:

- Project URL → `SUPABASE_URL`
- `anon` `public` key → `SUPABASE_ANON_KEY`

В `android/zal/local.properties`:

```properties
sdk.dir=/path/to/Android/Sdk
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
```

## 4. Пересобрать APK

```bash
cd android/zal && ./gradlew assembleDebug
```

На вкладке **Облако** должно быть «Supabase подключён». Кнопка «Синхронизировать сейчас» и автосинк при сохранении подходов/замеров.

## Безопасность

Схема для **личного** использования: RLS разрешает anon читать/писать таблицы.
Не публикуйте anon key в открытый маркет без ужесточения политик (auth.uid()).
