#!/usr/bin/env bash
# Экспорт постов TG-каналов для аудита в Gemini.
# Использование: ./scripts/export_gemini_tg_audit.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/audit/gemini_export"
DB="$ROOT/empire.db"

if [[ ! -f "$DB" ]]; then
  echo "Нет $DB" >&2
  exit 1
fi

mkdir -p "$OUT"
PERSONAS=(gdepar stern lenin garden pension)

for p in "${PERSONAS[@]}"; do
  sqlite3 "$DB" "
    SELECT '=== ' || persona_key || ' | id=' || id || ' | ' || datetime(created_at) || ' | decision=' || COALESCE(decision,'') || ' ===' || char(10) ||
           'TOPIC: ' || COALESCE(topic_raw,'') || char(10) ||
           'LEN: ' || LENGTH(text_content) || ' | IMG: ' || CASE WHEN image_path IS NOT NULL AND image_path != '' THEN 'yes' ELSE 'no' END || char(10) ||
           '---' || char(10) ||
           text_content || char(10) || char(10)
    FROM post_drafts
    WHERE persona_key='$p' AND status='published'
    ORDER BY created_at DESC;
  " > "$OUT/${p}_published.txt"
done

: > "$OUT/all_channels_last40.txt"
for p in "${PERSONAS[@]}"; do
  {
    echo "########## CHANNEL: $p (last 40) ##########"
    sqlite3 "$DB" "
      SELECT '=== ' || persona_key || ' | id=' || id || ' | ' || datetime(created_at) || ' ===' || char(10) ||
             'TOPIC: ' || COALESCE(topic_raw,'') || char(10) ||
             text_content || char(10) || char(10)
      FROM post_drafts
      WHERE persona_key='$p' AND status='published'
      ORDER BY created_at DESC LIMIT 40;
    "
    echo ""
  } >> "$OUT/all_channels_last40.txt"
done

sqlite3 "$DB" "
SELECT persona_key, status, COUNT(*) as cnt,
  ROUND(AVG(LENGTH(text_content))) as avg_len,
  MIN(date(created_at)) as first_pub,
  MAX(date(created_at)) as last_pub,
  SUM(CASE WHEN image_path IS NOT NULL AND image_path != '' THEN 1 ELSE 0 END) as with_img,
  SUM(CASE WHEN decision='auto' THEN 1 ELSE 0 END) as auto_cnt,
  SUM(CASE WHEN decision IN ('approved','approve') THEN 1 ELSE 0 END) as approved_cnt
FROM post_drafts WHERE status='published'
GROUP BY persona_key ORDER BY cnt DESC;
" > "$OUT/stats_summary.tsv"

sqlite3 "$DB" "
SELECT persona_key, status, COUNT(*) FROM post_drafts
WHERE status IN ('pending','draft','rejected')
GROUP BY persona_key, status ORDER BY persona_key, status;
" > "$OUT/backlog_summary.tsv"

sqlite3 "$DB" "
SELECT persona_key, topic_raw, COUNT(*) as cnt
FROM post_drafts WHERE status='published' AND topic_raw IS NOT NULL AND topic_raw != ''
GROUP BY persona_key, topic_raw
ORDER BY persona_key, cnt DESC;
" > "$OUT/topics_distribution.tsv"

sqlite3 "$DB" "
SELECT 'gdepar_kirilych', COUNT(*) FROM post_drafts WHERE persona_key='gdepar' AND status='published' AND text_content LIKE '%Кириллыч%'
UNION ALL SELECT 'gdepar_classic_banya', COUNT(*) FROM post_drafts WHERE persona_key='gdepar' AND status='published' AND text_content LIKE '%Классическая баня%'
UNION ALL SELECT 'gdepar_gdepar_link', COUNT(*) FROM post_drafts WHERE persona_key='gdepar' AND status='published' AND (text_content LIKE '%gdepar.ru%' OR text_content LIKE '%гдепар%')
UNION ALL SELECT 'stern_mamatov', COUNT(*) FROM post_drafts WHERE persona_key='stern' AND status='published' AND text_content LIKE '%Маматов%'
UNION ALL SELECT 'stern_joints', COUNT(*) FROM post_drafts WHERE persona_key='stern' AND status='published' AND text_content LIKE '%сустав%'
UNION ALL SELECT 'stern_hashtag_heavy', COUNT(*) FROM post_drafts WHERE persona_key='stern' AND status='published' AND (LENGTH(text_content)-LENGTH(REPLACE(text_content,'#',''))) > 5
UNION ALL SELECT 'lenin_calendar', COUNT(*) FROM post_drafts WHERE persona_key='lenin' AND status='published' AND text_content LIKE '%календарь%'
UNION ALL SELECT 'lenin_pss', COUNT(*) FROM post_drafts WHERE persona_key='lenin' AND status='published' AND text_content LIKE '%ПСС%'
UNION ALL SELECT 'garden_lunar', COUNT(*) FROM post_drafts WHERE persona_key='garden' AND status='published' AND text_content LIKE '%Лунный календарь%'
UNION ALL SELECT 'garden_weather', COUNT(*) FROM post_drafts WHERE persona_key='garden' AND status='published' AND (text_content LIKE '%погод%' OR text_content LIKE '%ЦФО%')
UNION ALL SELECT 'pension_raw_news', COUNT(*) FROM post_drafts WHERE persona_key='pension' AND status='published' AND text_content LIKE '%bbbreaking%';
" > "$OUT/pattern_flags.tsv"

echo "OK → $OUT"
wc -l "$OUT"/*.txt "$OUT"/*.tsv 2>/dev/null | tail -5
