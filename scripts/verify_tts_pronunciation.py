#!/usr/bin/env python3
"""Verify TTS pronunciation pipeline: gold text + optional Yandex TTS→STT CER.

Usage:
  python3 scripts/verify_tts_pronunciation.py              # SAMPLE + gold text
  python3 scripts/verify_tts_pronunciation.py --synth      # + A/B one phrase
  python3 scripts/verify_tts_pronunciation.py --cer        # gold TTS→STT CER
  python3 scripts/verify_tts_pronunciation.py --cer --cer-limit 8
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_md_for_tts import prepare_for_tts  # noqa: E402

SAMPLE = (
    'АО «Вектор» и ООО «Ромашка» продали много акций. '
    "Ненецкий АО остаётся регионом. Немного позже пришёл ИП Иванов."
)

GOLD_PATH = ROOT / "scripts" / "tts_gold_phrases.txt"

# SpeechKit markup / stress — STT этого не вернёт
_PHONEME_BLOCK = re.compile(r"\[\[([^\]]*)\]\]")
_OTHER_MARKUP = re.compile(
    r"sil<\[\d+\]>"
    r"|<\[[a-z]+\]>"
    r"|\+"
    r"|[\u0301]",
    re.I,
)


def _phoneme_to_word_map() -> dict[str, str]:
    """Обратный словарь: содержимое [[…]] → орфография (для CER ref)."""
    from tts_pronunciation import load_pronunciation_dict

    out: dict[str, str] = {}
    for src, dst in load_pronunciation_dict().items():
        d = dst.strip()
        if d.startswith("[[") and d.endswith("]]"):
            inner = d[2:-2].strip()
            out[inner] = src
            out[re.sub(r"\s+", " ", inner)] = src
    return out


_PHONEME_WORD: dict[str, str] | None = None


def _phoneme_word(inner: str) -> str:
    global _PHONEME_WORD
    if _PHONEME_WORD is None:
        _PHONEME_WORD = _phoneme_to_word_map()
    key = re.sub(r"\s+", " ", inner.strip())
    return _PHONEME_WORD.get(key) or _PHONEME_WORD.get(inner.strip()) or ""



def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _api_key() -> str:
    return (os.getenv("YANDEX_API_KEY") or os.getenv("SPEECHKIT_API_KEY") or "").strip()


def _folder_id() -> str:
    return (os.getenv("YANDEX_FOLDER_ID") or os.getenv("YC_FOLDER_ID") or "").strip()


def parse_gold(path: Path = GOLD_PATH) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        src = parts[0].strip()
        need = parts[1].strip()
        stt = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else None
        rows.append({"line": str(line_no), "src": src, "need": need, "stt": stt})
    return rows


def run_gold(*, accent: bool = False) -> list[str]:
    """Проверка must_contain по gold."""
    rows = parse_gold()
    if not rows:
        return [f"нет данных в {GOLD_PATH}"]
    errs: list[str] = []
    for row in rows:
        prepared = prepare_for_tts(str(row["src"]), accent=accent)
        low = prepared.lower()
        alts = [a.strip() for a in str(row["need"]).split("|") if a.strip()]
        if not any(a.lower() in low or a in prepared for a in alts):
            errs.append(
                f"gold:{row['line']}: {row['src']!r} → ожидалось одно из {alts}, "
                f"получили: {prepared.strip()!r}"
            )
    return errs


def check_text(prepared: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"(?<![А-Яа-яЁё])АО(?![А-Яа-яЁё])", prepared):
        errors.append("остался голый токен АО")
    if re.search(r"(?<![А-Яа-яЁё])ООО(?![А-Яа-яЁё])", prepared):
        errors.append("остался голый токен ООО")
    if "акционерное общество" not in prepared.lower():
        errors.append("нет расшифровки АО→акционерное общество")
    if "автономный округ" not in prepared.lower():
        errors.append("гео-АО не стало «автономный округ»")
    if "[[m n ɔ g ʌ]]" not in prepared:
        errors.append("нет фонем для «много»")
    if re.search(r"(?<![\[\w])много(?![\]\w])", prepared, flags=re.I):
        errors.append("осталось слово «много» без фонем")
    if re.search(r"(?<![\[\w])немного(?![\]\w])", prepared, flags=re.I):
        errors.append("осталось слово «немного» без фонем")
    if "индивидуальный предприниматель" not in prepared.lower():
        errors.append("ИП не расшифрован")
    return errors


def strip_tts_markup(text: str) -> str:
    """Текст «как должно звучать» без разметки SpeechKit — для CER ref.

    Блоки [[фонемы]] → орфография из словаря (иначе ref='акций' при 'много').
    """
    t = _PHONEME_BLOCK.sub(lambda m: _phoneme_word(m.group(1)) or "", text)
    t = _OTHER_MARKUP.sub("", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def normalize_for_cer(text: str) -> str:
    t = text.casefold().replace("ё", "е")
    t = re.sub(r"[^a-zа-я0-9]+", "", t, flags=re.I)
    return t


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def char_error_rate(ref: str, hyp: str) -> float:
    r, h = normalize_for_cer(ref), normalize_for_cer(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return levenshtein(r, h) / len(r)


def _post_form(url: str, data: dict[str, str], *, key: str, timeout: float = 120.0) -> bytes:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Api-Key {key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def synth_chunk_raw(
    text: str,
    out: Path,
    *,
    voice: str = "filipp",
    speed: str = "0.95",
    fmt: str = "mp3",
) -> None:
    key = _api_key()
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "format": fmt,
        "speed": speed,
    }
    fid = _folder_id()
    if fid:
        data["folderId"] = fid
    audio = _post_form(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        data,
        key=key,
    )
    if len(audio) < 500:
        raise RuntimeError(f"TTS too short: {len(audio)} bytes")
    out.write_bytes(audio)


def recognize_audio(path: Path, *, fmt: str = "oggopus") -> str:
    key = _api_key()
    params = {"lang": "ru-RU", "format": fmt, "topic": "general"}
    fid = _folder_id()
    if fid:
        params["folderId"] = fid
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?" + urllib.parse.urlencode(
        params
    )
    req = urllib.request.Request(
        url,
        data=path.read_bytes(),
        headers={
            "Authorization": f"Api-Key {key}",
            "Content-Type": "application/octet-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("result") or "").strip()


_BAD_STT = (
    "аоао",
    "мнов",
    "мэлэн",
    "м л н",
    "эмэлэн",
)


def _needles_ok(heard: str, spec: str) -> bool:
    """stt_needles: 'a|b;c|d' → (a OR b) AND (c OR d)."""
    low = heard.casefold().replace("ё", "е")
    for group in spec.split(";"):
        alts = [a.strip().casefold().replace("ё", "е") for a in group.split("|") if a.strip()]
        if alts and not any(a in low for a in alts):
            return False
    return True


def run_cer_suite(
    *,
    limit: int = 12,
    max_cer: float = 0.35,
    voice: str = "filipp",
    accent: bool = False,
) -> tuple[list[str], list[dict]]:
    """TTS→STT по gold-строкам с 3-й колонкой. Возвращает (errors, rows)."""
    rows = [r for r in parse_gold() if r.get("stt")]
    if limit > 0:
        rows = rows[:limit]
    if not rows:
        return (["CER: нет строк с stt_needles в gold"], [])

    work = Path(tempfile.mkdtemp(prefix="tts_cer_"))
    errors: list[str] = []
    results: list[dict] = []
    for i, row in enumerate(rows, 1):
        src = str(row["src"])
        prepared = prepare_for_tts(src, accent=accent).strip()
        # в синтез — с разметкой; в ref CER — без неё
        ref = strip_tts_markup(prepared)
        ogg = work / f"{i:03d}.ogg"
        try:
            synth_chunk_raw(prepared, ogg, voice=voice, fmt="oggopus")
            time.sleep(0.12)
            heard = recognize_audio(ogg, fmt="oggopus")
        except Exception as exc:
            errors.append(f"CER:{row['line']} {src!r}: API {exc}")
            results.append({"src": src, "error": str(exc)})
            continue

        cer = char_error_rate(ref, heard)
        bad = [b for b in _BAD_STT if b in heard.casefold()]
        needles_fail = not _needles_ok(heard, str(row["stt"]))
        # Hard-fail: запрещённые глюки SpeechKit + провал иголок.
        # CER — метрика (STT пишет «21»/«100$»/«букс»); порог только warn.
        rec = {
            "line": row["line"],
            "src": src,
            "prepared": prepared,
            "ref": ref,
            "heard": heard,
            "cer": round(cer, 4),
            "bad": bad,
            "needles_fail": needles_fail,
        }
        results.append(rec)
        flag = ""
        if cer > max_cer and not needles_fail and not bad:
            flag = " (cer-warn)"
        print(
            f"CER[{i}/{len(rows)}] line={row['line']} cer={cer:.3f}{flag} "
            f"src={src!r} heard={heard!r}"
        )
        if bad:
            errors.append(f"CER:{row['line']} запрещённые фрагменты {bad}: {heard!r}")
        if needles_fail:
            errors.append(
                f"CER:{row['line']} нет иголок {row['stt']!r} в STT: {heard!r}"
            )
    return errors, results


def main() -> int:
    p = argparse.ArgumentParser(description="TTS preprocess gold + optional CER")
    p.add_argument("--synth", action="store_true", help="A/B одна фраза TTS+STT")
    p.add_argument("--cer", action="store_true", help="прогнать gold TTS→STT CER")
    p.add_argument("--cer-limit", type=int, default=12, help="макс. фраз в CER (0=все)")
    p.add_argument("--max-cer", type=float, default=0.35, help="порог CER (доля ошибок)")
    p.add_argument("--gold", action="store_true", default=True)
    p.add_argument("--no-gold", action="store_true")
    p.add_argument("--voice", default="filipp")
    args = p.parse_args()

    os.environ["PDF_AUDIO_STRESS"] = "0"
    os.environ["PDF_AUDIO_PHONEMES"] = "1"
    os.environ["PDF_AUDIO_TTS_PROVIDER"] = "yandex"
    os.environ["PDF_AUDIO_PROSODY"] = "1"

    prepared = prepare_for_tts(SAMPLE, accent=False)
    print("=== PREPARED TEXT ===")
    print(prepared)
    errs = check_text(prepared)
    if errs:
        print("TEXT FAIL:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("TEXT OK")

    if args.gold and not args.no_gold:
        gold_errs = run_gold(accent=False)
        if gold_errs:
            print("GOLD FAIL:")
            for e in gold_errs:
                print(f"  - {e}")
            return 1
        n = len(parse_gold())
        print(f"GOLD OK: {n} phrases in {GOLD_PATH.name}")

    if args.cer:
        _load_env()
        if not _api_key():
            print("CER SKIP: нет YANDEX_API_KEY")
            return 0
        print(f"=== CER suite (limit={args.cer_limit}, max_cer={args.max_cer}) ===")
        cer_errs, results = run_cer_suite(
            limit=args.cer_limit,
            max_cer=args.max_cer,
            voice=args.voice,
            accent=False,
        )
        out_dir = ROOT / "tmp"
        out_dir.mkdir(parents=True, exist_ok=True)
        report = out_dir / "tts_cer_report.json"
        report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"CER report: {report}")
        if results:
            ok = [r for r in results if "cer" in r]
            if ok:
                avg = sum(float(r["cer"]) for r in ok) / len(ok)
                print(f"CER avg={avg:.3f} n={len(ok)}")
        if cer_errs:
            print("CER FAIL:")
            for e in cer_errs:
                print(f"  - {e}")
            return 1
        print("CER OK")

    if not args.synth:
        return 0

    _load_env()
    if not _api_key():
        print("SYNTH SKIP: нет YANDEX_API_KEY")
        return 0

    with tempfile.TemporaryDirectory(prefix="tts_pron_") as td:
        work = Path(td)
        raw_probe = "АО Вектор продало много акций."
        fixed_probe = "Акционерное общество Вектор продало [[m n ɔ g ʌ]] акций."
        try:
            raw_ogg = work / "raw.ogg"
            fixed_ogg = work / "fixed.ogg"
            synth_chunk_raw(raw_probe, raw_ogg, fmt="oggopus", voice=args.voice)
            synth_chunk_raw(fixed_probe, fixed_ogg, fmt="oggopus", voice=args.voice)
            raw_heard = recognize_audio(raw_ogg, fmt="oggopus")
            heard = recognize_audio(fixed_ogg, fmt="oggopus")
        except Exception as exc:
            print(f"SYNTH/STT FAIL: {exc}")
            return 1
        print(f"=== STT raw  === {raw_heard!r}")
        print(f"=== STT fixed === {heard!r}")
        print(f"=== CER fixed === {char_error_rate(strip_tts_markup(fixed_probe), heard):.3f}")
        heard_l = heard.lower()
        stt_errs: list[str] = []
        if re.search(r"(^|[^а-я])ао([^а-я]|$)", heard_l):
            stt_errs.append("STT слышит голое «АО» на fixed")
        if "мнов" in heard_l:
            stt_errs.append("STT слышит «мново»")
        if "акционерн" not in heard_l:
            stt_errs.append("нет «акционерн»")
        if stt_errs:
            print("STT FAIL:")
            for e in stt_errs:
                print(f"  - {e}")
            return 1
        print("STT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
