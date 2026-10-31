"""Еженедельный аудит качества постов Empire (curated vs LLM-мусор)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

try:
    import content_p0
except ImportError:
    content_p0 = None  # type: ignore[assignment]

try:
    import gdepar_content
except ImportError:
    gdepar_content = None  # type: ignore[assignment]

try:
    import lenin_content
except ImportError:
    lenin_content = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent

# Слоты, которые по матрице должны быть curated (без LLM-разворота).
_CURATED_TOPIC_MARKERS = (
    "[Дуэт]",
    "[Классическая баня]",
    "[SPECIAL:",
    "[#Вэтотдень]",
    "[ПСС · фрагмент]",
    "[Сказка на ночь]",
    "[Ленин в ",
    "[Ленин ·",
    "[Рутина]",
    "[Психология]",
    "[Восстановление]",
    "[История гирь]",
    "[Историческое наследие]",
    "[Спортмед",
    "[Экипировка",
    "[Техника гирь]",
    "[Лунный календарь]",
    "[План на неделю]",
    "[Разбор полетов]",
    "[Тест недели]",
)

_LLM_LEAK_MARKERS = (
    "Свободная тема",
    "[Марксистский анализ]",
    "[План на день]",
    "[Почва]",
    "[Питание]",
    "[Биомеханика]",
    "[Рутина] ",
)

_CLICHE_BY_PERSONA: dict[str, tuple[str, ...]] = {
    "stern": (
        r"гиря\s*—\s*не просто",
        r"не просто .{0,30}снаряд",
        r"маматов",
        r"актуально сегодня",
    ),
    "gdepar": (
        # Обращение «Кириллыч, …» — клише; лейбл реплики «Кириллыч:» — норма.
        r"кириллыч\s*[,—\-–]\s*",
        r"слушай,?\s*кириллыч",
        r"актуально сегодня",
        r"парадокс\?",
    ),
    "garden": (
        r"учёные доказали",
        r"исследования показали",
        r"раскрой свой потенциал",
    ),
    "lenin": (
        r"актуально сегодня",
        r"сим победиши",
        r"парадокс\?",
    ),
}


@dataclass
class DraftFinding:
    draft_id: int
    persona_key: str
    topic_raw: str
    decision: str
    status: str
    issues: list[str] = field(default_factory=list)


def _is_curated_topic(topic_raw: str | None) -> bool:
    t = topic_raw or ""
    return any(m in t for m in _CURATED_TOPIC_MARKERS)


def _is_llm_slot_topic(topic_raw: str | None) -> bool:
    t = topic_raw or ""
    return any(m in t for m in _LLM_LEAK_MARKERS)


def audit_text(text: str, persona_key: str, *, topic_raw: str = "") -> list[str]:
    """Причины брака / предупреждения для одного поста."""
    issues: list[str] = []
    if not text or text.startswith("🛑"):
        issues.append("пустой или ошибка API")
        return issues

    if content_p0:
        for f in content_p0.p0_findings(text, persona_key):
            issues.append(f)

    if persona_key == "gdepar" and gdepar_content:
        for f in gdepar_content.preachy_findings(text, topic_raw):
            issues.append(f"preachy: {f}")

    if persona_key == "lenin" and lenin_content and lenin_content.is_press_polemic_story(text):
        issues.append("lenin: повтор сюжета «пресса/полемика»")

    low = text.lower()
    topic = topic_raw or ""
    for pat in _CLICHE_BY_PERSONA.get(persona_key, ()):
        if persona_key == "gdepar" and "[Дуэт]" in topic and "кириллыч" in pat:
            continue
        if re.search(pat, low, re.IGNORECASE | re.MULTILINE):
            issues.append(f"клише: /{pat}/")

    tags = [t for t in text.split() if t.startswith("#")]
    if persona_key == "stern" and len(tags) > 3:
        issues.append(f"stern: {len(tags)} хэштегов (>3)")

    if persona_key in ("gdepar", "garden", "lenin") and _is_llm_slot_topic(topic_raw):
        if not _is_curated_topic(topic_raw):
            issues.append("LLM-слот (не curated marker)")

    return issues


def audit_draft_row(row: dict) -> DraftFinding:
    issues = audit_text(
        row.get("text_content") or "",
        row.get("persona_key") or "",
        topic_raw=row.get("topic_raw") or "",
    )
    topic = row.get("topic_raw") or ""
    if row.get("persona_key") == "pension":
        return DraftFinding(
            draft_id=row["id"],
            persona_key="pension",
            topic_raw=topic,
            decision=row.get("decision") or "",
            status=row.get("status") or "",
            issues=issues,
        )
    if _is_llm_slot_topic(topic) and row.get("decision") == "auto":
        issues.append("автопост LLM-слота")
    return DraftFinding(
        draft_id=row["id"],
        persona_key=row.get("persona_key") or "",
        topic_raw=topic,
        decision=row.get("decision") or "",
        status=row.get("status") or "",
        issues=issues,
    )


def load_recent_drafts(
    db_path: Path,
    *,
    days: int = 7,
    statuses: tuple[str, ...] = ("published", "pending"),
) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat(sep=" ", timespec="seconds")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in statuses)
    cur.execute(
        f"""
        SELECT id, persona_key, topic_raw, text_content, decision, status, created_at
        FROM post_drafts
        WHERE status IN ({placeholders})
          AND datetime(created_at) >= datetime(?)
          AND persona_key != 'pension'
        ORDER BY created_at DESC
        """,
        (*statuses, since),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def find_duplicate_topics(rows: list[dict], *, window_days: int = 21) -> list[str]:
    """topic_raw, опубликованные чаще 1 раза за окно."""
    from collections import Counter

    c: Counter[str] = Counter()
    for r in rows:
        if r.get("status") != "published":
            continue
        t = (r.get("topic_raw") or "").strip()
        if t and not t.startswith("Свободная"):
            c[t] += 1
    return [f"{t} (×{n})" for t, n in c.most_common() if n > 1]


def build_audit_report(
    db_path: Path | None = None,
    *,
    days: int = 7,
) -> str:
    db = db_path or ROOT / "empire.db"
    if not db.is_file():
        return f"⚠ content_audit: нет {db}"

    rows = load_recent_drafts(db, days=days)
    findings = [audit_draft_row(r) for r in rows]
    bad = [f for f in findings if f.issues]
    pending = [f for f in findings if f.status == "pending"]
    auto_llm = [
        f
        for f in findings
        if f.decision == "auto" and _is_llm_slot_topic(f.topic_raw) and not _is_curated_topic(f.topic_raw)
    ]

    by_persona: dict[str, list[DraftFinding]] = {}
    for f in bad:
        by_persona.setdefault(f.persona_key, []).append(f)

    dupes = find_duplicate_topics(rows)

    lines = [
        f"🔍 Empire · аудит контента ({days} дн.)",
        f"Проверено: {len(rows)} · с замечаниями: {len(bad)} · pending: {len(pending)}",
        "",
        "── По каналам (проблемные) ──",
    ]
    for pk in ("gdepar", "stern", "lenin", "garden"):
        items = by_persona.get(pk, [])
        if not items:
            lines.append(f"✅ {pk}: чисто ({sum(1 for r in rows if r.get('persona_key')==pk)} постов)")
            continue
        lines.append(f"⚠ {pk}: {len(items)} постов с замечаниями")
        for f in items[:5]:
            lines.append(f"  #{f.draft_id} {f.topic_raw[:55]}…")
            for iss in f.issues[:3]:
                lines.append(f"    · {iss[:100]}")

    if auto_llm:
        lines.extend(["", f"── Автопост LLM-слотов: {len(auto_llm)} (отключить) ──"])
        for f in auto_llm[:6]:
            lines.append(f"  #{f.draft_id} {f.persona_key}: {f.topic_raw[:60]}")

    if dupes:
        lines.extend(["", "── Повтор topic_raw (published) ──"])
        for d in dupes[:8]:
            lines.append(f"  · {d[:90]}")

    lines.extend(
        [
            "",
            "── Режим curated (цель) ──",
            "Пар: duo/classic/book/promo · Штерн: matrix+rubrics+video",
            "Ленин: рубрики+ПСС+календарь · Сад: луна+промо (остальное — вручную)",
            "",
            "Экспорт для Gemini: ./scripts/export_gemini_tg_audit.sh",
            "Матрица на завтра: ./venv/bin/python scripts/verify_posting_matrix.py",
        ]
    )
    return "\n".join(lines)


def reject_junk_pending(
    db_path: Path,
    *,
    dry_run: bool = True,
    personas: tuple[str, ...] = ("garden", "lenin", "gdepar", "stern"),
) -> list[int]:
    """Отклонить pending с явным LLM-мусором (Свободная тема, P0, клише)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, persona_key, topic_raw, text_content, decision, status
        FROM post_drafts
        WHERE status = 'pending' AND persona_key IN ({})
        """.format(",".join("?" * len(personas))),
        personas,
    )
    rejected: list[int] = []
    for row in cur.fetchall():
        r = dict(row)
        issues = audit_text(
            r.get("text_content") or "",
            r.get("persona_key") or "",
            topic_raw=r.get("topic_raw") or "",
        )
        topic = r.get("topic_raw") or ""
        junk = (
            topic.startswith("Свободная тема")
            or any(i.startswith("P0:") for i in issues)
            or (r.get("persona_key") == "garden" and "[План на день]" in topic)
            or (
                r.get("persona_key") == "stern"
                and "[Рутина]" in topic
                and "STR-" not in topic
                and "вариант" not in topic.lower()
            )
        )
        if not junk:
            continue
        rejected.append(r["id"])
        if not dry_run:
            cur.execute(
                "UPDATE post_drafts SET decision='rejected', status='rejected', decided_at=datetime('now') WHERE id=?",
                (r["id"],),
            )
    if not dry_run:
        conn.commit()
    conn.close()
    return rejected
