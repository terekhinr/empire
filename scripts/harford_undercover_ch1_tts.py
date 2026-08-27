#!/usr/bin/env python3
"""Extract Harford ch1 (annotation+intro+ch1) → clean TTS → Gemini MP3 → Telegram."""
from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empire_notify import send, send_file  # noqa: E402
from prepare_md_for_tts import prepare_for_tts  # noqa: E402

PDF = ROOT / "data" / "book" / "Тим Харфорд Экономист под прикрытием.pdf"
OUT_DIR = ROOT / "data" / "audio" / "harford_undercover"
STEM = "ekonomist_pod_prikrytiem_annot_intro_ch1"

# Combining acute after stressed vowel — helps Gemini Russian stress.
ACUTE = "\u0301"

# Inline footnotes → short spoken asides (option 2). Bibliographic URLs omitted.
INLINE_NOTES: dict[str, str] = {
    "1": "Фильм Клинта Иствуда «Непрощённый», тысяча девятьсот девяносто второй год.",
    "2": "Классический вестерн «Ровно в полдень», тысяча девятьсот пятьдесят второй год.",
    "3": "Речь о скачке нефтяных цен середины двухтысячных.",
    "4": "Актуа́рии — специалисты по страховой математике и оценке рисков.",
}

CHAPTER_BRIEF_NOTES = (
    "Кратко по источникам главы. Модель ренты — у Давида Рикардо в «Началах "
    "политической экономии и налогового обложения». Экономика уличных банд — "
    "у Стивена Левитта и Судхира Венкатеша. Себестоимость чашки кофе и влияние "
    "аренды на прибыль кофеен подтверждены отраслевыми исследованиями и "
    "публикациями Financial Times. Статистика по иммиграции и зарплатам — "
    "у Мартина Вулфа и Джорджа Борхаса."
)

INTRO_BRIEF_NOTES = (
    "Кратко по источникам введения. Образ сложной кооперации незнакомцев "
    "восходит к Полю Сибрайту, книге «Компания незнакомцев»."
)


def _stress_renta_match(m: re.Match[str]) -> str:
    word = m.group(0)
    # ре́нта… — economic rent
    return word[:2] + ACUTE + word[2:]


# Brand / finance pronunciation before generic symbol cleanup.
SPEECH_LEXICON: list[tuple[re.Pattern[str], str | callable]] = [
    (re.compile(r"\bFinancial Times\b"), "Файнэншл Таймс"),
    (re.compile(r"\bAmazon\.com\b", re.I), "Амазон"),
    (re.compile(r"\bWhole Foods\b"), "Хоул Фудс"),
    (re.compile(r"\bStarbucks\b"), "Старбакс"),
    (re.compile(r"\bCaribou Coffee\b"), "Карибу Кофи"),
    (re.compile(r"\bJava House\b"), "Джава Хаус"),
    (re.compile(r"\bCapitol Grounds\b"), "Кэпитол Граундс"),
    (re.compile(r"\bTeaism\b"), "Тиизм"),
    (re.compile(r"\bSwing'?s\b"), "Свингз"),
    (re.compile(r"\bCosi\b"), "Кози"),
    (re.compile(r"\bAMT\b"), "эй эм ти"),
    (re.compile(r"\bWal-?Mart\b"), "Уолмарт"),
    (re.compile(r"\bShell\b"), "Шелл"),
    (re.compile(r"\bCosta Coffee\b"), "Коста Кофи"),
    (re.compile(r"\bCosta\b"), "Коста"),
    (re.compile(r"\bCaf[eé]direct\b", re.I), "Кафе директ"),
    (re.compile(r"\bNetwork Rail\b"), "Нетворк Рейл"),
    (re.compile(r"\bNBER\b"), "эн би и ар"),
    (re.compile(r"\bФаррагут Вест\b"), f"Фарра{ACUTE}гут Вест"),
    (re.compile(r"\bИнтернэшнл-сквер\b"), f"Интернэ{ACUTE}шнл-сквер"),
    (re.compile(r"\bВатерлоо\b"), f"Ва{ACUTE}терлоо"),
    (re.compile(r"\bШиньюку\b"), f"Синдзю{ACUTE}ку"),
    (re.compile(r"\bДавид(а|у|ом)? Рикардо\b"), rf"Дави{ACUTE}д\1 Рика{ACUTE}рдо"),
    (re.compile(r"\bСтивен(а|у)? Левитт\b"), rf"Сти{ACUTE}вен\1 Ле{ACUTE}витт"),
    (re.compile(r"\bСудхир(а|у)? Венкатеш\b"), rf"Судхи{ACUTE}р\1 Венка{ACUTE}теш"),
    (re.compile(r"\bБернард(а)? Шоу\b"), rf"Бе{ACUTE}рнард\1 Шоу"),
    (re.compile(r"\bактуарии\b", re.I), f"актуа{ACUTE}рии"),
    (re.compile(r"\bактуариев\b", re.I), f"актуа{ACUTE}риев"),
    (re.compile(r"\bмаржинальн", re.I), f"маржина{ACUTE}льн"),
    (re.compile(r"\b(рент[аыуе]|рентой|рентою)\b", re.I), _stress_renta_match),
    (re.compile(r"£\s*(\d+(?:[.,]\d+)?)"), r"\1 фунтов стерлингов"),
    (re.compile(r"\$\s*(\d+(?:[.,]\d+)?)"), r"\1 долларов"),
    (re.compile(r"\bXXI\b"), "двадцать первого"),
    (re.compile(r"\bXVIII\b"), "восемнадцатого"),
]


def extract_pages(pdf: Path, start: int, end: int) -> str:
    import fitz

    doc = fitz.open(pdf)
    parts: list[str] = []
    for i in range(start, end):
        text = doc[i].get_text("text")
        # Drop trailing bare page numbers.
        text = re.sub(r"\n\s*\d{1,3}\s*$", "\n", text)
        parts.append(text)
    return "\n".join(parts)


def fix_pdf_artifacts(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\xa0", " ")
    # Rejoin hyphenated line breaks: "мага-\nзин" → "магазин"
    text = re.sub(r"([А-Яа-яЁёA-Za-z])-\n([а-яёa-z])", r"\1\2", text)
    # Collapse soft line wraps inside paragraphs (keep blank lines).
    lines = text.split("\n")
    out: list[str] = []
    buf = ""
    for line in lines:
        raw = line.rstrip()
        stripped = raw.strip()
        if not stripped:
            if buf:
                out.append(buf.strip())
                buf = ""
            if out and out[-1] != "":
                out.append("")
            continue
        # Standalone page number
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        if not buf:
            buf = stripped
            continue
        # New paragraph cues: ALL CAPS block start, headings, *** 
        if stripped in {"***", "•"}:
            out.append(buf.strip())
            out.append("")
            buf = ""
            continue
        if re.match(r"^(Глава\s+\d+|Введение|Аннотация|Annotation|Власть дефицита|Спорная тема|Как быть экономистам|Вернёмся)\b", stripped):
            out.append(buf.strip())
            out.append("")
            buf = stripped
            continue
        # Join wrapped lines
        if buf.endswith(("-", "—")):
            buf = buf[:-1] + stripped
        elif buf[-1:] in ".!?:;»\"" and stripped[:1].isupper():
            out.append(buf.strip())
            buf = stripped
        else:
            buf = f"{buf} {stripped}"
    if buf:
        out.append(buf.strip())
    text = "\n".join(out)
    # Known OCR / layout glitches
    text = text.replace("выставляются м продаются", "выставляются и продаются")
    text = text.replace("национальной без опасности", "национальной безопасности")
    text = text.replace("кофейными киоскам", "кофейным киоскам")
    return text


def fix_all_caps_runs(text: str) -> str:
    def _fix(m: re.Match[str]) -> str:
        s = m.group(0)
        if len(s) < 24:
            return s
        lower = s.lower()
        return lower[0].upper() + lower[1:]

    text = re.sub(r"(?:[А-ЯЁ]{2,}(?:[\s,—\-–]+[А-ЯЁ]{2,}){3,})", _fix, text)
    # Restore proper nouns flattened by ALL-CAPS fold (chapter openings).
    proper = {
        r"\bнью-йорк\b": "Нью-Йорк",
        r"\bтокио\b": "Токио",
        r"\bантверпен\b": "Антверпен",
        r"\bпрага\b": "Прага",
        r"\bлондон\b": "Лондон",
        r"\bвашингтон\b": "Вашингтон",
        r"\bгонконг\b": "Гонконг",
        r"\bмоскв([аеуы])\b": r"Москв\1",
        r"\bманхэттен\b": "Манхэттен",
        r"\bвест-энд\b": "Вест-Энд",
        r"\bвеликобритани([яию])\b": r"Великобритани\1",
        r"\bамерик([аеиу])\b": r"Америк\1",
        r"\bкита([йяю])\b": r"Кита\1",
        r"\bсаудовск": "Саудовск",
        r"\bирак": "Ирак",
        r"\bнигери": "Нигери",
        r"\bвенесуэл": "Венесуэл",
        r"\bкувейт": "Кувейт",
        r"\bрикардо\b": "Рикардо",
    }
    for pat, repl in proper.items():
        text = re.sub(pat, repl, text, flags=re.I)
    text = re.sub(r"\b[Вв] [Лл]юбом\b", "в любом", text)
    text = re.sub(r"Глава\s+1\b", "Глава первая.", text)
    return text


def inject_inline_notes(text: str) -> str:
    def _repl(m: re.Match[str]) -> str:
        num = m.group(1)
        note = INLINE_NOTES.get(num)
        if not note:
            return ""
        return f" (Примечание: {note})"

    return re.sub(r"\[(\d+)\]", _repl, text)


def apply_lexicon(text: str) -> str:
    for pat, repl in SPEECH_LEXICON:
        if callable(repl):
            text = pat.sub(repl, text)
        else:
            text = pat.sub(repl, text)
    return text


def trim_annotation(raw: str) -> str:
    # Stop before author/TOC bleed-through (line breaks may already be collapsed).
    for pat in (
        r"Тим Харфорд\s+Благодарности",
        r"\bБлагодарности\s+Введение\b",
        r"\bТим Харфорд\b",
    ):
        cut = re.search(pat, raw)
        if cut:
            raw = raw[: cut.start()]
            break
    raw = re.sub(r"^Annotation\s*", "Аннотация.\n\n", raw)
    # Drop any leftover TOC crumbs.
    raw = re.sub(
        r"(?:Глава\s+\d+\s*){2,}.*$",
        "",
        raw,
        flags=re.S,
    )
    return raw.strip()


def strip_toc_bleed(text: str) -> str:
    text = re.sub(
        r"(?:Глава\s+\d+\s*){3,}(?:Введение\s*)?",
        "",
        text,
    )
    text = re.sub(r"Благодарности\s+Введение", "Введение", text)
    return text


def build_manuscript(pdf: Path) -> str:
    # Pages: 1 annotation, 7-9 intro, 10-31 chapter 1 (0-based: 1, 7-9, 10-31)
    annotation = trim_annotation(fix_pdf_artifacts(extract_pages(pdf, 1, 2)))
    intro = fix_pdf_artifacts(extract_pages(pdf, 7, 10))
    chapter = fix_pdf_artifacts(extract_pages(pdf, 10, 32))

    intro = inject_inline_notes(intro)
    chapter = inject_inline_notes(chapter)

    # Title card for listener
    title = (
        "Тим Харфорд. Экономист под прикрытием.\n\n"
        "Фрагмент: аннотация, введение и глава первая.\n\n"
    )

    intro_body = intro.strip()
    if not intro_body.lower().startswith("введение"):
        intro_body = "Введение.\n\n" + intro_body
    intro_body = intro_body + f"\n\n{INTRO_BRIEF_NOTES}\n"

    ch_body = chapter.strip()
    ch_body = ch_body + f"\n\n{CHAPTER_BRIEF_NOTES}\n"

    raw = "\n\n".join([title, annotation, intro_body, ch_body])
    raw = strip_toc_bleed(raw)
    raw = fix_all_caps_runs(raw)
    raw = apply_lexicon(raw)
    cleaned = prepare_for_tts(raw)
    # prepare_for_tts strips [n] already handled; restore spaced en-dash pauses lightly
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def patch_gemini_prompt() -> None:
    import docx_to_mp3_gemini as g

    g.PROMPT_PREFIX = (
        "Прочитай вслух по-русски как профессиональный диктор финансовой аудиокниги. "
        "Спокойный уверенный тембр, живые интонации, естественный темп без театральности. "
        "Соблюдай ударения (в том числе знаки ударения в тексте). "
        "Денежные суммы, проценты и англицизмы произноси по-русски, как в подготовленном тексте. "
        "Не произноси знаки препинания, скобки, номера страниц и несуществующие символы. "
        "Не делай пауз на переносах строк внутри предложения. "
        "Пауза только в конце предложений и абзацев. "
        "Текст:\n\n"
    )
    g.RETRIES = 8
    g.MAX_CHUNK = 2200


def synth(text_path: Path, mp3_path: Path, voice: str) -> int:
    import docx_to_mp3_gemini as g

    patch_gemini_prompt()
    # Stronger 429 backoff
    orig_synth = g.synth_chunk

    def synth_with_backoff(client, model, voice_name, text):
        last_exc: Exception | None = None
        for attempt in range(1, g.RETRIES + 1):
            try:
                return orig_synth(client, model, voice_name, text)
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                wait = 5 * attempt
                m = re.search(r"retry in ([0-9.]+)s", msg, re.I)
                if m:
                    wait = max(wait, int(float(m.group(1))) + 2)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = max(wait, 45)
                print(f"  backoff {wait}s: {msg[:160]}", flush=True)
                time.sleep(wait)
        assert last_exc is not None
        raise last_exc

    g.synth_chunk = synth_with_backoff  # type: ignore[assignment]

    sys.argv = [
        "docx_to_mp3_gemini.py",
        str(text_path),
        "-o",
        str(mp3_path),
        "--voice",
        voice,
        "--resume",
        "--keep-chunks",
    ]
    return g.main()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=PDF)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--voice", default="charon")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--synth-only", action="store_true")
    parser.add_argument("--send-only", action="store_true")
    parser.add_argument("--no-send", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    text_path = args.out_dir / f"{STEM}_tts.txt"
    mp3_path = args.out_dir / f"{STEM}.mp3"

    if not args.synth_only and not args.send_only:
        if not args.pdf.is_file():
            print(f"Missing PDF: {args.pdf}", file=sys.stderr)
            return 1
        manuscript = build_manuscript(args.pdf)
        text_path.write_text(manuscript, encoding="utf-8")
        print(f"TTS text: {text_path} ({len(manuscript)} chars)")

    if args.prepare_only:
        return 0

    if not args.send_only:
        send(
            "🎙 Харфорд «Экономист под прикрытием»: "
            "озвучка аннотации + введения + главы 1 (голос Charon)…"
        )
        rc = synth(text_path, mp3_path, args.voice)
        if rc != 0:
            send(f"❌ Ошибка озвучки Харфорда (код {rc}).")
            return rc

    if args.no_send:
        print(f"MP3 ready (not sent): {mp3_path}")
        return 0

    if not mp3_path.is_file():
        print(f"Missing MP3: {mp3_path}", file=sys.stderr)
        return 1

    size_mb = mp3_path.stat().st_size / (1024 * 1024)
    label = "Харфорд — Экономист под прикрытием (аннот.+введ.+гл.1)"
    send(f"✅ Готово: {label}\n{size_mb:.1f} МБ — отправляю файл…")
    ok = send_file(mp3_path, caption=label, as_audio=True)
    if not ok:
        send("❌ Не удалось отправить MP3 в Telegram.")
        return 2
    send("✅ Файл отправлен.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
