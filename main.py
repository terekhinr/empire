import asyncio
import html as html_std
import httpx
import os
import re
import json
import logging
import time
import urllib.parse
import pytz
import base64
import random
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, LinkPreviewOptions

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, select, desc, text, func, and_, or_

os.environ["TOKENIZERS_PARALLELISM"] = "false"
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

try:
    from rss_maker import generate_zen_rss
except ImportError:
    generate_zen_rss = None

try:
    from analytics_db import log_event as analytics_log_event
except ImportError:
    def analytics_log_event(*_a, **_kw):  # noqa: ANN001
        pass

try:
    import gdepar_content
except ImportError:
    gdepar_content = None  # type: ignore[assignment]

try:
    import content_p0
except ImportError:
    content_p0 = None  # type: ignore[assignment]

try:
    import lenin_content
except ImportError:
    lenin_content = None  # type: ignore[assignment]

try:
    import garden_content
except ImportError:
    garden_content = None  # type: ignore[assignment]

try:
    import pension_content
except ImportError:
    pension_content = None  # type: ignore[assignment]

try:
    import stern_content
except ImportError:
    stern_content = None  # type: ignore[assignment]

import rubric_posts

# --- 1. НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone("Europe/Moscow")


def msk_now() -> datetime:
    """Europe/Moscow — единая TZ для слотов расписания и weekday()."""
    return datetime.now(MSK_TZ)


load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMPIRE_ROOT = Path(__file__).resolve().parent
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///empire.db")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

os.makedirs("media/lenin", exist_ok=True)
os.makedirs("media/references", exist_ok=True)
os.makedirs("data", exist_ok=True)
if os.getenv("EMPIRE_SKIP_EMBEDDINGS", "").strip().lower() in ("1", "true", "yes"):
    embeddings = None  # тесты и скрипты без загрузки HF-модели
else:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

@event.listens_for(engine.sync_engine, "connect")
def _sqlite_set_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()

class PostDraft(Base):
    __tablename__ = "post_drafts"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String)
    text_content = Column(Text)
    image_prompt = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    # — добавлено для feedback loop / памяти тем —
    topic_raw = Column(Text, nullable=True)
    decision = Column(String, nullable=True)  # approved | rejected | pending
    decided_at = Column(DateTime, nullable=True)
    regen_count = Column(Integer, default=0)
    bad_image_count = Column(Integer, default=0)


class TopicHistory(Base):
    """Лог использованных тем для дедупликации и подсказок «другой ракурс»."""
    __tablename__ = "topic_history"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String, index=True)
    topic_norm = Column(String, index=True)
    topic_raw = Column(Text)
    draft_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BanyaSpot(Base):
    """Общественная баня для карты gdepar.ru."""
    __tablename__ = "banya_spots"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True)
    title = Column(String)
    city = Column(String, index=True)
    region = Column(String, index=True, nullable=True)  # 'MO' | 'SPB' | 'MSK' | 'LO' (источник OSM)
    osm_id = Column(String, index=True, nullable=True)
    address = Column(String)
    lat = Column(String)  # храним как строку, чтобы не возиться с floats в sqlite
    lon = Column(String)
    heating = Column(String)  # 'wood' | 'electric' | 'mixed' | 'unknown'
    kind = Column(String)     # 'public' | 'private'
    site_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    yandex_url = Column(String, nullable=True)
    twogis_url = Column(String, nullable=True)
    cover_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    clips_json = Column(Text, nullable=True)     # JSON-список ссылок на 15-сек ролики
    tags_json = Column(Text, nullable=True)      # JSON-список ["парилка", "купель", "веники"]
    visited = Column(Integer, default=0)         # 0/1 — были ли лично
    status = Column(String, default="draft", index=True)  # 'draft' | 'published' | 'hidden'
    rating_avg = Column(String, nullable=True)   # кэш среднего рейтинга по сайтам
    reviews_total = Column(Integer, default=0)
    price_from = Column(Integer, nullable=True)
    price_per_hour = Column(Integer, nullable=True)
    capacity_max = Column(Integer, nullable=True)
    has_pool = Column(Integer, default=0)
    has_tub = Column(Integer, nullable=True)
    own_venik_allowed = Column(Integer, nullable=True)
    bath_style = Column(String, nullable=True)
    district = Column(String, nullable=True)
    partner_tier = Column(String, default="free")
    owner_account_id = Column(Integer, nullable=True)
    map_views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BanyaLead(Base):
    __tablename__ = "banya_leads"
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, index=True, nullable=False)
    lead_type = Column(String, index=True, nullable=False)
    source = Column(String, default="site")
    session_id = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Publication(Base):
    """Статус публикации черновика по каналу (ТЗ FINAL §4.1)."""
    __tablename__ = "publications"
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, index=True)
    channel = Column(String, index=True)
    source_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    external_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsItem(Base):
    """RSS-новости (дедуп по url_hash)."""
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    url_hash = Column(String, unique=True, index=True)
    url = Column(String)
    title = Column(Text)
    source_feed = Column(String)
    category = Column(String, index=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class SpySignal(Base):
    """Аномалии конкурентов (Telethon или dry-run)."""
    __tablename__ = "spy_signals"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String, index=True)
    competitor = Column(String)
    post_url = Column(String, nullable=True)
    post_text = Column(Text, nullable=True)
    post_ref = Column(String, index=True)
    er_proxy = Column(String, nullable=True)
    anomaly_score = Column(String, nullable=True)
    status = Column(String, default="new", index=True)
    draft_id = Column(Integer, nullable=True)
    source = Column(String, default="dry_run")
    created_at = Column(DateTime, default=datetime.utcnow)


class NeurocommentPlan(Base):
    """Планируемые комментарии (dry-run)."""
    __tablename__ = "neurocomment_plans"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String, index=True, nullable=True)
    channel_ref = Column(String)
    post_ref = Column(String)
    planned_text = Column(Text)
    reason = Column(Text, nullable=True)
    status = Column(String, default="dry_run", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShortsScript(Base):
    """Сценарий Shorts для съёмки."""
    __tablename__ = "shorts_scripts"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String, index=True)
    title = Column(String)
    hook = Column(Text)
    bullets_json = Column(Text)
    cta = Column(Text)
    duration_sec = Column(Integer, default=20)
    broll_json = Column(Text, nullable=True)
    trend_ref = Column(String, nullable=True)
    status = Column(String, default="ready", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    """Очередь фоновых задач для empire_worker.py."""
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    job_type = Column(String, index=True)
    status = Column(String, default="pending", index=True)
    payload_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class BanyaReview(Base):
    """Отзыв о бане из внешнего источника (или собственный)."""
    __tablename__ = "banya_reviews"
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, index=True)
    source = Column(String, index=True)          # 'yandex' | '2gis' | 'otzovik' | 'manual'
    source_id = Column(String, index=True)       # внешний id отзыва (для дедупа)
    author = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)      # 1..5
    text = Column(Text)
    url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending", index=True)  # pending|approved|hidden|spam


async def _alter_post_drafts_schema(conn) -> None:
    """Идемпотентная миграция: добавляет новые колонки в post_drafts, если их нет.
    SQLite поддерживает `ADD COLUMN`, повторное добавление падает — ловим."""
    new_cols = [
        ("topic_raw", "TEXT"),
        ("decision", "VARCHAR"),
        ("decided_at", "DATETIME"),
        ("regen_count", "INTEGER DEFAULT 0"),
        ("bad_image_count", "INTEGER DEFAULT 0"),
    ]
    for col, ddl in new_cols:
        try:
            await conn.execute(text(f"ALTER TABLE post_drafts ADD COLUMN {col} {ddl}"))
        except Exception:
            # Колонка уже есть — игнорируем.
            pass


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=30000"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.run_sync(Base.metadata.create_all)
        await _alter_post_drafts_schema(conn)


async def enqueue_job(job_type: str, payload: dict | None = None) -> int:
    """Добавить задачу в очередь jobs (обрабатывает empire_worker)."""
    async with async_session() as session:
        job = Job(
            job_type=job_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return int(job.id)

with open("content_config.json", "r", encoding="utf-8") as f:
    CONTENT_CONFIG = json.load(f)

try:
    with open("data/post_format.json", "r", encoding="utf-8") as f:
        POST_FORMAT = json.load(f)
except Exception:
    POST_FORMAT = {"telegram_mention": {}, "pension_video": {}, "pension_ps": {}}

def _pension_tg_chat_target() -> str | None:
    """ID канала или @username для автопоста pension (из env или PENSION_TG_URL)."""
    explicit = os.getenv("PENSION_TG_CHAT_ID", "").strip()
    if explicit:
        return explicit
    url = (os.getenv("PENSION_TG_URL") or "https://t.me/pensiya_nikogda").strip() or "https://t.me/pensiya_nikogda"
    m = re.match(r"https?://t\.me/([A-Za-z0-9_]+)/?", url)
    if m:
        return f"@{m.group(1)}"
    return None


def _platform_targets() -> dict[str, dict[str, str | None]]:
    return {
        "garden": {"tg": "-1002008085075"},
        "lenin": {"tg": "-1002136411597"},
        "stern": {"tg": "-1002024827297"},
        "gdepar": {"tg": "-1003960332245"},
        "pension": {"tg": _pension_tg_chat_target()},
    }


PLATFORM_TARGETS = _platform_targets()

PERSONAS = {
    "garden": {
        "model": "deepseek/deepseek-chat", 
        "role": "Агроном Степаныч. Природное земледелие. Пишешь сразу по делу, БЕЗ фраз вроде 'Советы от Степаныча' или 'Приветствую'.", 
        "style": "Highly realistic rustic gardening photography, soft natural lighting, focus on details and textures"
    },
    "lenin": {
        "model": "deepseek/deepseek-chat", 
        "role": "В.И. Ленин. Исторический архив.", 
        "style": "Soviet agitprop poster style, constructivism"
    },
    "stern": {
        "model": "deepseek/deepseek-chat",
        "role": (
            "Канал «Снегири · здоровый позвоночник» — методист по спине, кору, осанке. "
            "Гири — инструмент, не соревновательный гиревой спорт. "
            "Пишешь как старший в зале: коротко по форме, развёрнуто по сути. "
            "Опираешься на МакГилла (Big-3, Back Mechanic) и умеренную работу с гирей."
        ),
        "style": "Gritty raw fitness photography, dark gym atmosphere, realistic 8k"
    },
    "gdepar": {
        "model": "deepseek/deepseek-chat",
        "role": (
            "Дуэт банщиков: Михалыч (30 лет в бане) и Кириллыч (стройка, печи, цифры). "
            "Михалыч — пар, веник, этикет, быт; Кириллыч — вентиляция, материалы, экономика. "
            "Иногда короткий спор, всегда по делу. Простой русский, без проповеди. "
            "Не использует слова: 'священнодействие', 'братство', 'варварство', 'обновлённый', "
            "'загоняй поколения', 'крестись', 'выгоняй из себя'. "
            "Не пишет про 'душу' и 'равенство'. TG дополняет gdepar.ru — карта и отзывы на сайте."
        ),
        # Жёстко фиксируем визуал русской бани и БАННЫЙ веник (venik из берёзы/дуба),
        # запрещаем хозяйственную метлу/щётку. Английский — для fal/flux.
        "style": (
            "Authentic traditional Russian banya (parilka) interior, hand-hewn log walls, "
            "polished wooden benches, wood-fired sauna stove with hot stones, faint steam in the air, "
            "warm amber lamp light, highly realistic photography. "
            "If a venik appears, it must be a traditional Russian BIRCH OR OAK BATH WHISK (banya venik) — "
            "leafy bundle of fresh birch or oak twigs with leaves, tied with twine, used for parenie. "
            "STRICT NEGATIVE: no household sweeping broom, no straw broom, no cleaning broom, "
            "no twig broom for floors, no dustpan, no kitchen tools."
        )
    },
    "pension": {
        "model": "deepseek/deepseek-chat",
        "role": (
            "Аналитик финансов и личных стратегий. Пишешь авторский разбор: тезис → факты "
            "из источников (Талеб, Хулиномика, Капитал, актуальные новости) → вывод. "
            "Запрещено: пересказывать «личную стратегию канала» как универсальный факт, "
            "ссылаться на канал/книгу «На пенсию в 35», упоминать @pensiya35 и его контент "
            "(это конкурирующий проект Бабайкина). "
            "Если вспоминаешь авторов — называй их по фамилии (Талеб, Марков), а не по номеру источника."
        ),
        "style": "stylized financial chart"
    }
}

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_and_increment_stern_counter():
    counter_file = "data/stern_counter.txt"
    try:
        with open(counter_file, "r") as f:
            num = int(f.read().strip())
    except:
        num = 1
    with open(counter_file, "w") as f:
        f.write(str(num + 1))
    return num

def _md_links_to_telegram_html(text: str) -> str:
    from telegram_md import md_links_to_telegram_html

    return md_links_to_telegram_html(text)


_PROMPT_LABEL = (
    # допускаем markdown-обвязку: **PROMPT:**, ### PROMPT:, __PROMPT__:, *PROMPT*:, > PROMPT:
    r"(?:\*{1,3}|_{1,3}|\#{1,6}|>|\s)*"
    r"(?:промпт|промт|prompt|image[\s_-]?prompt|img[\s_-]?prompt|picture[\s_-]?prompt"
    r"|промпт[\s_-]?для[\s_-]?картинки)"
    r"(?:\*{1,3}|_{1,3})*"
)


def _strip_leaked_service_lines(text: str) -> str:
    """Убираем служебные хвосты, если модель засунула их в ТЕКСТ."""
    lines = text.splitlines()
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if re.match(rf"(?i)^{_PROMPT_LABEL}\s*:", s):
            break
        if re.match(r"(?i)^промпт\s+для\s+картинки", s):
            continue
        m_tekst = re.match(r"(?i)^\s*текст\s*:\s*(.*)$", ln)
        if m_tekst:
            rest = (m_tekst.group(1) or "").strip()
            if rest:
                out.append(rest)
            continue
        out.append(ln)
    text = "\n".join(out)
    text = re.sub(r"(?i)\bпромпт\s+для\s+картинки[^\n.]*\.?", "", text)
    return text


_HASHTAG_TOKEN = re.compile(r"#[\wа-яА-ЯёЁ\d_]+", re.UNICODE)
_CYRILLIC_TOKEN = re.compile(r"[А-Яа-яЁё]")


def _split_trailing_english_prompt(text: str) -> tuple[str, str | None]:
    """Если модель забыла поставить «ПРОМПТ:», но в хвосте всё равно есть
    большой английский абзац — отделяем его как промпт.

    Возвращает (clean_text, image_prompt or None). Эвристика: ищем последний
    «английский кластер» — подряд идущие непустые строки, в которых нет ни
    одной кириллической буквы и есть хотя бы 3 пробела (т.е. это абзац,
    а не строка хэштегов). Перед ним должна быть пустая строка или строка
    хэштегов / служебных символов.
    """
    lines = text.rstrip().splitlines()
    n = len(lines)
    if n < 2:
        return text, None

    # ищем индексы непустых строк
    end = n - 1
    while end >= 0 and not lines[end].strip():
        end -= 1
    if end < 0:
        return text, None

    # двигаемся вверх, пока строки английские (нет кириллицы)
    start = end
    while start > 0:
        s = lines[start].strip()
        if not s:
            break
        if _CYRILLIC_TOKEN.search(s):
            break
        start -= 1
    if start == end:
        # одна-единственная строка — может быть хэштеги; не трогаем
        s_only = lines[end].strip()
        if s_only.startswith("#"):
            return text, None
        # если одиночная строка содержит хотя бы 3 пробела и латиницу — это хвостовой промпт
        if " " in s_only and len(s_only.split()) >= 4 and re.search(r"[A-Za-z]", s_only):
            cleaned = "\n".join(lines[:end]).rstrip()
            return cleaned, s_only
        return text, None

    # block = строки [start+1 .. end] — английский абзац
    eng_block = "\n".join(lines[start + 1 : end + 1]).strip()
    if not eng_block:
        return text, None
    # минимальная «весомость» — должен быть осмысленный английский (хотя бы 4 слова и латиница)
    if len(eng_block.split()) < 4 or not re.search(r"[A-Za-z]", eng_block):
        return text, None
    # если это просто строка с хэштегами на латинице — не трогаем
    if all(w.startswith("#") for w in eng_block.split()):
        return text, None

    cleaned = "\n".join(lines[: start + 1]).rstrip()
    return cleaned, eng_block


_TEKST_LABEL_BLOCK = re.compile(
    # допускаем любые markdown-обёртки (* / ** / *** / #) и пробелы вокруг «ТЕКСТ»
    r"(?is)^[\s\ufeff]*(?:[*_#>]+\s*)?текст(?:[*_#]+)?\s*:\s*(?:[*_#]+)?\s*\n*",
)


def _strip_leading_tekst_label(text: str) -> str:
    """Убирает «ТЕКСТ:» и `**ТЕКСТ:**` / `### ТЕКСТ:` в начале ответа (несколько раз подряд)."""
    t = text.lstrip("\ufeff \t\r\n")
    while True:
        n = _TEKST_LABEL_BLOCK.sub("", t, count=1)
        if n == t:
            break
        t = n
    return t


def _strip_orphan_markdown_lines(text: str) -> str:
    """Строки из одних * / ** без текста."""
    lines = [ln for ln in text.splitlines() if ln.strip() not in ("*", "**", "***", "****")]
    return "\n".join(lines).strip()


def _peel_hashtag_suffix_lines(text: str) -> tuple[str, list[str]]:
    """
    Снимает с конца поста строки с хэштегами (в т.ч. «ломаную» строку модели),
    возвращает тело и список уникальных тегов в порядке появления снизу вверх по блоку.
    """
    lines = text.rstrip().split("\n")
    collected: list[str] = []
    seen_lower: set[str] = set()

    def add_from_string(s: str) -> None:
        for m in _HASHTAG_TOKEN.finditer(s):
            tag = m.group(0)
            tl = tag.lower()
            if tl not in seen_lower:
                seen_lower.add(tl)
                collected.append(tag)

    while lines:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if last in ("*", "**", "***"):
            lines.pop()
            continue
        words = last.split()
        if not words:
            lines.pop()
            continue
        ht = sum(1 for w in words if w.startswith("#") and len(w) > 1)
        if ht == 0:
            break
        if ht == len(words):
            add_from_string(last)
            lines.pop()
            continue
        if ht >= max(2, (len(words) + 1) // 2):
            add_from_string(last)
            lines.pop()
            continue
        break

    collected.reverse()
    body = "\n".join(lines).strip()
    return body, collected


def _hashtag_from_rubric(rubric_plain: str | None) -> str | None:
    """Один хэштег из рубрики; Obsidian и мусор в заголовке не превращаем в #...[кавычки]."""
    if not rubric_plain or not str(rubric_plain).strip():
        return None
    raw = str(rubric_plain).strip()
    if raw.lower().startswith("[obsidian]"):
        return "#obsidian"
    core = re.sub(r'[\[\]()"\'«».,!?;:—–\-]+', " ", raw)
    token = "".join(core.split())
    if len(token) < 2 or len(token) > 48:
        return None
    return "#" + token


_HASHTAG_LIMIT_BY_PERSONA = {
    "stern": 3,
    "gdepar": 4,
    "lenin": 3,
    "garden": 3,
    "pension": 3,
}


def _merge_hashtag_line(
    peeled_tags: list[str],
    p_key: str,
    rubric_plain: str | None,
    topic_raw: str | None = None,
) -> str:
    """Один ряд хэштегов: рубрика → уже найденные → добор из дефолтов, без дублей."""
    ordered: list[str] = []
    seen: set[str] = set()

    def push(raw: str) -> None:
        t = raw.strip()
        if not t.startswith("#"):
            return
        tl = t.lower()
        if tl in seen:
            return
        seen.add(tl)
        ordered.append(t)

    tag_src = list(peeled_tags)
    if p_key == "gdepar" and gdepar_content and topic_raw:
        tag_src = gdepar_content.filter_hashtags_for_topic(topic_raw, tag_src)

    rubric_tag = _hashtag_from_rubric(rubric_plain)
    if rubric_tag:
        push(rubric_tag)
    for t in tag_src:
        push(t)
    for t in _default_hashtag_line(p_key, None).split():
        push(t)
    limit = _HASHTAG_LIMIT_BY_PERSONA.get(p_key, 6)
    return " ".join(ordered[:limit])


def _default_hashtag_line(p_key: str, rubric_plain: str | None) -> str:
    parts: list[str] = []
    rubric_tag = _hashtag_from_rubric(rubric_plain)
    if rubric_tag:
        parts.append(rubric_tag)
    tail = {
        "stern": ["#снегири"],
        "garden": ["#огород", "#дача"],
        "gdepar": ["#баня", "#гдепар"],
        "lenin": ["#история", "#ленин"],
        "pension": ["#финансы", "#мысль"],
    }.get(p_key, ["#контент"])
    limit = _HASHTAG_LIMIT_BY_PERSONA.get(p_key, 6)
    for t in tail:
        if t.lower() not in [p.lower() for p in parts]:
            parts.append(t)
    return " ".join(parts[:limit])


def build_pension_video_crosspost_block() -> str:
    """Готовый HTML блок ссылок на площадки (только для Пенсии + видео)."""
    v = POST_FORMAT.get("pension_video") or {}
    ps = POST_FORMAT.get("pension_ps") or {}
    lines: list[str] = []
    for url, label in (
        (v.get("youtube"), "СМОТРЕТЬ В YOUTUBE"),
        (v.get("vk"), "СМОТРЕТЬ НА ВК"),
        (v.get("rutube"), "СМОТРЕТЬ В RUTUBE"),
    ):
        u = (url or "").strip()
        if u:
            lines.append(f'📺 <a href="{html_std.escape(u, quote=True)}">{label}</a>')
    if not lines:
        return ""
    block = "\n".join(lines)
    mu = (ps.get("max_url") or "").strip()
    if mu:
        ml = ps.get("max_label", "MAX")
        block += (
            f'\n\nP.S.\n💬 <a href="{html_std.escape(mu, quote=True)}">'
            f"{html_std.escape(ml)}</a>"
        )
    b1u = (ps.get("book1_url") or "").strip()
    b1t = ps.get("book1_title", "книга")
    b2u = (ps.get("book2_url") or "").strip()
    b2t = ps.get("book2_title", "книга")
    pp: list[str] = []
    if b1u:
        pp.append(f'P.P.S.\n<a href="{html_std.escape(b1u, quote=True)}">{html_std.escape(b1t)}</a>')
    if b2u:
        pp.append(f'<a href="{html_std.escape(b2u, quote=True)}">{html_std.escape(b2t)}</a>')
    if pp:
        block += "\n\n" + "\n\n".join(pp)
    return block


def _strip_citation_markers(text: str) -> str:
    """Убирает квадратные ссылки на источники RAG ([1], [3-5], [2,4], [1; 3]) из публичного текста."""
    protected: list[str] = []

    def _stash(m: re.Match) -> str:
        protected.append(m.group(0))
        return f"\x00PRE{len(protected) - 1}\x00"

    text = re.sub(
        r"<pre>.*?</pre>|<code>.*?</code>",
        _stash,
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"\s*\[\d{1,2}(?:\s*[\-–,;]\s*\d{1,2})*\]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    for i, block in enumerate(protected):
        text = text.replace(f"\x00PRE{i}\x00", block)
    return text


def finalize_public_post(
    text: str,
    p_key: str,
    rubric_plain: str | None,
    is_pension_video: bool,
    topic_raw: str | None = None,
) -> str:
    """Хэштеги снизу (одна строка, без дублей), опционально блок ссылок для Пенсии+видео, @канала."""
    t = text.strip()
    t = re.sub(r"(\n\n)?@\w+\s*$", "", t, flags=re.IGNORECASE)
    t = _strip_orphan_markdown_lines(t)
    t = _strip_citation_markers(t)

    video_block = ""
    if p_key == "pension" and is_pension_video:
        video_block = build_pension_video_crosspost_block()

    body, peeled_tags = _peel_hashtag_suffix_lines(t)
    if p_key == "gdepar" and gdepar_content:
        body = gdepar_content.strip_kirilych_opening(body)
    tag_line = _merge_hashtag_line(
        peeled_tags, p_key, rubric_plain, topic_raw=topic_raw or rubric_plain
    )

    parts_out = [body]
    if video_block:
        parts_out.append(video_block)
    parts_out.append(tag_line)

    mention = (POST_FORMAT.get("telegram_mention") or {}).get(p_key, "").strip()
    joined = "\n\n".join(p for p in parts_out if p)
    if mention:
        joined = f"{joined}\n\n{mention}"
    return joined.strip()


# Опечатки/устаревшие формы, которые DeepSeek любит для редких слов.
# Применяем ТОЛЬКО для stern, чтобы не задеть «гира» в исторических текстах Ленина или
# «кору» в постах про сад/деревья.
_STERN_TYPOS: list[tuple[re.Pattern, str]] = [
    # «гира/гиру/гирой/гирами/гирах» (мужская форма) → нормальные склонения «гиря»
    (re.compile(r"\bГира\b"), "Гиря"),
    (re.compile(r"\bгира\b"), "гиря"),
    (re.compile(r"\bгиры\b"), "гири"),
    (re.compile(r"\bгире\b(?![:м])"), "гире"),  # форма совпадает, не трогаем
    (re.compile(r"\bгиру\b"), "гирю"),
    (re.compile(r"\bгирой\b"), "гирей"),
    (re.compile(r"\bГиром\b"), "Гирей"),
    (re.compile(r"\bгиром\b"), "гирей"),
    # «Кора» в смысле мышцы — модель сваливается в женский род от слова «кора (дерева)».
    # Контексты: «Кора играет/работает/держит/стабилизирует/обеспечивает …»
    (re.compile(r"\bКора\s+(играет|работает|держит|стабилизирует|обеспечивает|должна|должн|перед|нагру)"),
     r"Кор \1"),
    (re.compile(r"\bкора\s+(играет|работает|держит|стабилизирует|обеспечивает|должна|должн|перед|нагру)"),
     r"кор \1"),
    # «активация коры» в смысле мышц → «активация кора»
    (re.compile(r"\bактивац[ии][ия]\s+коры\b"), "активация кора"),
]


def _apply_stern_typos(text: str) -> str:
    for pat, repl in _STERN_TYPOS:
        text = pat.sub(repl, text)
    return text


_TELEGRAM_HTML_TAG_RE = re.compile(
    r"</?(b|i|u|s|code|pre|a|blockquote)(\s[^>]*)?>",
    re.IGNORECASE,
)


def _normalize_markdown_emphasis(text: str) -> str:
    """***жирный+курсив*** в Obsidian → **жирный** (иначе ломается порядок <b>/<i>)."""
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"**\1**", text)
    text = re.sub(r"___(.+?)___", r"__\1__", text)
    return text


def _balance_telegram_html_tags(text: str) -> str:
    """Закрывает b/i/… в порядке стека — Telegram не принимает <b><i>x</b></i>."""
    out: list[str] = []
    stack: list[str] = []
    pos = 0
    for m in _TELEGRAM_HTML_TAG_RE.finditer(text):
        out.append(text[pos : m.start()])
        raw = m.group(0)
        tag = (m.group(1) or "").lower()
        if not tag:
            pos = m.end()
            continue
        if raw.startswith("</"):
            while stack and stack[-1] != tag:
                out.append(f"</{stack.pop()}>")
            if stack and stack[-1] == tag:
                stack.pop()
                out.append(raw)
            pos = m.end()
            continue
        stack.append(tag)
        out.append(raw)
        pos = m.end()
    out.append(text[pos:])
    while stack:
        out.append(f"</{stack.pop()}>")
    return "".join(out)


def fix_html_safety(text):
    """Очистка текста от мусора нейросети и конвертация Markdown в Telegram HTML."""
    parts = re.split(rf"(?im)^\s*{_PROMPT_LABEL}\s*:\s*\*{{0,3}}\s*$", text, maxsplit=1)
    if len(parts) == 1:
        parts = re.split(rf"(?i)\n\s*{_PROMPT_LABEL}\s*:", text, maxsplit=1)
    clean_text = parts[0]
    clean_text = _strip_leading_tekst_label(clean_text)
    clean_text = re.sub(r"(?i)^ТЕКСТ\s*:\s*", "", clean_text)
    clean_text = _strip_leaked_service_lines(clean_text)
    clean_text = re.sub(r"\n-{3,}\s*\n?", "\n\n", clean_text)
    clean_text = _strip_orphan_markdown_lines(clean_text)

    # Исправляем слипшиеся слова (например, ТегСлово -> Тег Слово)
    clean_text = re.sub(r"(?<=[а-яa-z])(?=[А-ЯA-Z])", " ", clean_text)

    from telegram_md import (
        enrich_obsidian_markdown,
        md_angle_links_to_telegram_html,
        md_bare_urls_to_telegram_html,
    )

    clean_text = enrich_obsidian_markdown(clean_text)
    clean_text = _normalize_markdown_emphasis(clean_text)
    clean_text = _md_links_to_telegram_html(clean_text)
    clean_text = md_angle_links_to_telegram_html(clean_text)

    # Заголовки markdown (# слово) — не путать с хэштегами (#слово без пробела после решётки)
    def _heading_sub(m: re.Match) -> str:
        return f"<b>{m.group(1)}</b>"

    clean_text = re.sub(r"^#+\s+(.+)$", _heading_sub, clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean_text)
    clean_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", clean_text)
    clean_text = md_bare_urls_to_telegram_html(clean_text)
    clean_text = clean_text.replace("`", "")
    clean_text = re.sub(r"(?m)^\s*\*{2,}\s*$", "", clean_text)

    clean_text = re.sub(r"Советы от Степаныча[:\.\-]?\s*", "", clean_text, flags=re.IGNORECASE)
    clean_text = _balance_telegram_html_tags(clean_text)

    return clean_text.strip()

def calculate_old_style(day, month, year):
    try:
        dt = datetime(year, month, day)
        offset = 13 if year >= 1900 else 12
        old_dt = dt - timedelta(days=offset)
        months_ru = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        return f"{old_dt.day} {months_ru[old_dt.month - 1]}"
    except:
        return "[вычисли дату]"

def get_lenin_calendar_event():
    try:
        now = datetime.now(MSK_TZ)
        today_str = f"{now.day:02d}.{now.month:02d}." 
        file_path = "data/lenin/revolutionary_calendar.txt"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(today_str):
                        return line.strip()
    except: pass
    return None

def get_lenin_book_chunk():
    queue_file = "data/lenin_books_queue.json"
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
            if queue:
                chunk = queue.pop(0)
                with open(queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue, f, ensure_ascii=False, indent=4)
                return chunk
        except: pass
    return None

def encode_image_to_base64(filepath):
    with open(filepath, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded}"

LENIN_POOL_DIR = "media/lenin/pool"


def _pick_random_lenin_from_pool(d_id: int) -> str | None:
    """Берёт случайный портрет Ленина из локального пула и копирует под event_{id}.jpg."""
    if not os.path.isdir(LENIN_POOL_DIR):
        return None
    candidates = [
        os.path.join(LENIN_POOL_DIR, f)
        for f in os.listdir(LENIN_POOL_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
        and os.path.getsize(os.path.join(LENIN_POOL_DIR, f)) > 50_000
    ]
    if not candidates:
        return None
    src = random.choice(candidates)
    dst = f"media/lenin/event_{d_id}.jpg"
    try:
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        if os.path.getsize(dst) > 50_000:
            logger.info(f"[lenin] fallback to pool image: {os.path.basename(src)}")
            return dst
    except Exception:
        pass
    return None


def _is_lenin_article(title: str, query: str) -> bool:
    """Считаем статью «про Ленина», только если её заголовок содержит ключевое слово."""
    tl = (title or "").lower()
    return any(k in tl for k in ("ленин", "ульянов", "lenin", "ulyanov"))


async def fetch_wikipedia_image(query, d_id):
    clean_query = re.sub(r"[^a-zA-Zа-яА-Я0-9\s]", "", query).replace("В этот день в истории", "").strip()
    if len(clean_query) < 5:
        clean_query = "Ленин Владимир Ильич"
    search_url = (
        "https://ru.wikipedia.org/w/api.php?action=query&list=search"
        f"&srsearch={urllib.parse.quote(clean_query + ' Ленин')}&utf8=&format=json&srlimit=10"
    )
    headers = {"User-Agent": "EmpireBot/5.3 (https://neverretire.ru)"}

    img_source: str | None = None
    matched_title: str | None = None
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(search_url, headers=headers, timeout=10)
            search_data = res.json().get("query", {}).get("search", [])

            for hit in search_data:
                title = hit.get("title", "")
                if not _is_lenin_article(title, clean_query):
                    continue
                img_url_api = (
                    f"https://ru.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}"
                    "&prop=pageimages&format=json&piprop=original"
                )
                img_res = await client.get(img_url_api, headers=headers, timeout=10)
                pages = img_res.json().get("query", {}).get("pages", {})
                if not pages:
                    continue
                page = list(pages.values())[0]
                if "original" in page:
                    cand = page["original"]["source"]
                    if cand.lower().endswith((".jpg", ".jpeg", ".png")):
                        img_source = cand
                        matched_title = title
                        break
    except Exception:
        pass

    if img_source:
        try:
            async with httpx.AsyncClient() as client:
                path = f"media/lenin/event_{d_id}.jpg"
                file_res = await client.get(img_source, headers=headers, timeout=15)
                if file_res.status_code == 200 and len(file_res.content) > 50_000:
                    with open(path, "wb") as f:
                        f.write(file_res.content)
                    logger.info(f"[lenin] wiki image from '{matched_title}' -> {path}")
                    return path
                else:
                    logger.warning(
                        f"[lenin] wiki image failed status={file_res.status_code} size={len(file_res.content)} title={matched_title}"
                    )
        except Exception as e:
            logger.warning(f"[lenin] wiki image download error: {e}")

    return _pick_random_lenin_from_pool(d_id)


async def _lenin_wikipedia_image(
    *,
    prompt: str,
    d_id: int,
    topic_raw: str | None = None,
    topic_hint: str | None = None,
) -> str | None:
    """Wikimedia для Ленина: факт из слота → LLM-промпт → портрет Ленина."""
    style_prefix = (PERSONAS.get("lenin") or {}).get("style", "") + "."
    queries: list[str] = []

    if topic_hint and topic_hint.strip():
        queries.append(topic_hint.strip())
    if topic_raw and "[#Вэтотдень]" in topic_raw:
        headline = re.sub(r"^\[#\w+\]\s*", "", topic_raw).strip()
        if headline:
            queries.insert(0, headline)
    art = (prompt or "").replace(style_prefix, "").strip()
    if art and art.lower() not in {q.lower() for q in queries}:
        queries.append(art)
    queries.append("Ленин Владимир Ильич")

    seen: set[str] = set()
    for q in queries:
        key = q.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        img = await fetch_wikipedia_image(q, d_id)
        if img:
            return img
    return None


async def fetch_llm_response(
    model,
    user_prompt,
    *,
    temperature: float = 0.2,
    max_attempts: int = 3,
):
    """OpenRouter chat/completions с retry при битом JSON и 429/5xx."""
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
    }
    last_err: str | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0,
                )
            body = (resp.text or "").strip()
            if resp.status_code in (429, 502, 503, 504) or resp.status_code >= 500:
                last_err = f"OpenRouter HTTP {resp.status_code}"
                logger.warning(
                    "[llm] attempt %d/%d: %s body=%r",
                    attempt,
                    max_attempts,
                    last_err,
                    body[:200],
                )
                if attempt < max_attempts:
                    await asyncio.sleep(min(2 * attempt, 8))
                continue
            if not body:
                last_err = f"OpenRouter HTTP {resp.status_code}: пустой ответ"
                logger.warning("[llm] attempt %d/%d: %s", attempt, max_attempts, last_err)
                if attempt < max_attempts:
                    await asyncio.sleep(2)
                continue
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                last_err = f"OpenRouter: не JSON (HTTP {resp.status_code}): {e}"
                logger.warning(
                    "[llm] attempt %d/%d: JSONDecodeError %s; body[:240]=%r",
                    attempt,
                    max_attempts,
                    e,
                    body[:240],
                )
                if attempt < max_attempts:
                    await asyncio.sleep(2 * attempt)
                continue
            return resp.status_code, data
        except httpx.HTTPError as e:
            last_err = f"OpenRouter сеть: {e}"
            logger.warning("[llm] attempt %d/%d: %s", attempt, max_attempts, last_err)
            if attempt < max_attempts:
                await asyncio.sleep(2 * attempt)

    return 0, {"error": last_err or "OpenRouter: неизвестная ошибка"}


# ─────────────────────────────────────────────────────────────
#  Память тем (TopicHistory) — дедупликация и подсказка ракурса
# ─────────────────────────────────────────────────────────────

_TOPIC_NORM_RE = re.compile(r"[^a-zа-яё0-9]+", re.IGNORECASE)
# Слова без смысловой нагрузки: при сравнении тем игнорируем.
_TOPIC_STOP = {
    "и", "или", "а", "но", "что", "как", "это", "для", "на", "в", "по", "с", "со", "о", "об",
    "от", "до", "из", "у", "к", "за", "под", "над", "при", "же", "бы", "ли", "не", "ни",
    "так", "там", "тут", "там", "тоже", "также", "ещё", "уже", "the", "a", "an", "of",
    "и", "ли", "ну",
}


def _normalize_topic(topic_raw: str) -> str:
    """Нормализуем тему: lower, без рубрик [..], без пунктуации, без стоп-слов, сорт по алфавиту."""
    if not topic_raw:
        return ""
    s = re.sub(r"\[.*?\]", " ", topic_raw)  # вырезаем рубрику типа [Видео]
    s = s.lower()
    tokens = [t for t in _TOPIC_NORM_RE.split(s) if t and t not in _TOPIC_STOP and len(t) > 2]
    return " ".join(sorted(set(tokens)))


def _topic_jaccard(a: str, b: str) -> float:
    """Сходство тем по Жаккару на уровне токенов нормализованной строки."""
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


async def _recent_post_bodies(p_key: str, days: int = 21, limit: int = 20) -> list[str]:
    """Тексты недавних черновиков/публикаций — для антидубля тела поста."""
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session() as session:
        res = await session.execute(
            select(PostDraft)
            .where(PostDraft.persona_key == p_key)
            .where(PostDraft.created_at >= since)
            .where(PostDraft.text_content.isnot(None))
            .order_by(PostDraft.created_at.desc())
            .limit(limit)
        )
        rows = res.scalars().all()
    out: list[str] = []
    for r in rows:
        body = (r.text_content or "").strip()
        if len(body) > 80:
            out.append(body)
    return out


def _gdepar_body_duplicate_findings(text: str, recent_bodies: list[str]) -> list[str]:
    if not gdepar_content or not recent_bodies:
        return []
    findings: list[str] = []
    max_sim = 0.0
    for old in recent_bodies:
        sim = gdepar_content.body_jaccard(text, old)
        max_sim = max(max_sim, sim)
    if max_sim >= 0.72:
        findings.append(
            f"пост почти копия недавнего (сходство {max_sim:.0%}) — перепиши с нуля, другие примеры и зацепка"
        )
    elif max_sim >= 0.58:
        findings.append(
            f"слишком похож на недавний пост ({max_sim:.0%}) — смени структуру и конкретику"
        )
    return findings


async def _recent_topics(p_key: str, days: int = 30, limit: int = 60) -> list[dict]:
    """Возвращает темы по персоне за последние `days` дней."""
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session() as session:
        res = await session.execute(
            select(TopicHistory)
            .where(TopicHistory.persona_key == p_key)
            .where(TopicHistory.created_at >= since)
            .order_by(TopicHistory.created_at.desc())
            .limit(limit)
        )
        rows = res.scalars().all()
        return [
            {"topic_raw": r.topic_raw, "topic_norm": r.topic_norm, "created_at": r.created_at}
            for r in rows
        ]


async def _record_topic_history(p_key: str, topic_raw: str, draft_id: int | None) -> None:
    """Логируем использованную тему в TopicHistory."""
    norm = _normalize_topic(topic_raw)
    try:
        async with async_session() as session:
            session.add(TopicHistory(
                persona_key=p_key,
                topic_norm=norm,
                topic_raw=topic_raw,
                draft_id=draft_id,
            ))
            await session.commit()
    except Exception as e:
        logger.warning(f"[topic_history] save error: {e}")


async def _topic_history_hint(p_key: str, topic_raw: str) -> str:
    """Если похожая тема за 30 дней уже была — возвращаем инструкцию «новый ракурс»."""
    norm_cur = _normalize_topic(topic_raw)
    if not norm_cur:
        return ""
    recent = await _recent_topics(p_key, days=30)
    similar = [
        {"topic": r["topic_raw"], "at": r["created_at"].strftime("%Y-%m-%d")}
        for r in recent
        if _topic_jaccard(norm_cur, r["topic_norm"]) >= 0.55
    ]
    if not similar:
        return ""
    avoid_list = "; ".join(f"«{s['topic']}» ({s['at']})" for s in similar[:3])
    return (
        "ПАМЯТЬ ТЕМ: за последние 30 дней были похожие посты — " + avoid_list + ".\n"
        "Возьми НОВЫЙ ракурс: другой подсюжет, другие конкретные примеры/цифры/имена, "
        "другие ошибки или нюансы. НЕ повторяй структуру и тезисы предыдущих постов.\n"
    )


# ─────────────────────────────────────────────────────────────
#  Семейства тем в content_config: строка или {"variants": [...], "family": "..."}
# ─────────────────────────────────────────────────────────────

_VARIANT_PICK_LOOKBACK_DAYS = 14
_GDEPAR_VARIANT_LOOKBACK_DAYS = 28


def _slot_variants_from_value(slot_value) -> list[str] | None:
    """None → трактовать как одну строку (не список вариантов)."""
    if isinstance(slot_value, str):
        return None
    if isinstance(slot_value, list):
        out = [str(x).strip() for x in slot_value if str(x).strip()]
        return out or None
    if isinstance(slot_value, dict):
        if "variants" in slot_value:
            raw = slot_value["variants"]
            if not isinstance(raw, list):
                return []
            out = [str(x).strip() for x in raw if str(x).strip()]
            return out or []
        if isinstance(slot_value.get("topic"), str):
            t = slot_value["topic"].strip()
            return [t] if t else []
    return None


async def _pick_least_similar_variant(p_key: str, candidates: list[str]) -> str:
    """Выбираем вариант с наименьшей максимальной похожестью на недавние темы (разнообразие)."""
    clean = [c for c in candidates if c.strip()]
    if not clean:
        return "Свободная тема"
    if len(clean) == 1:
        return clean[0]
    lookback = _GDEPAR_VARIANT_LOOKBACK_DAYS if p_key == "gdepar" else _VARIANT_PICK_LOOKBACK_DAYS
    recent = await _recent_topics(p_key, days=lookback, limit=80)
    norms_recent = [r["topic_norm"] for r in recent if r.get("topic_norm")]
    recent_raw = [r["topic_raw"] for r in recent if r.get("topic_raw")]
    recent_raw_set = set(recent_raw)
    scored: list[tuple[float, float, float, float, str]] = []
    for c in clean:
        nc = _normalize_topic(c)
        if not norms_recent:
            sim = 0.0
        else:
            sim = max((_topic_jaccard(nc, nr) for nr in norms_recent), default=0.0)
        fam_pen = 0.0
        if p_key == "gdepar" and gdepar_content:
            fam_pen = gdepar_content.family_penalty_score(recent_raw, c)
        exact_pen = 8.0 if c in recent_raw_set else 0.0
        fam_mult = 0.28 if p_key == "gdepar" else 0.15
        scored.append((sim + fam_pen * fam_mult + exact_pen, sim, fam_pen, random.random(), c))
    scored.sort(key=lambda x: (x[0], x[1], x[3]))
    chosen = scored[0][4]
    if p_key == "gdepar" and gdepar_content and scored[0][2] >= 1.5:
        analytics_log_event(
            "gdepar_topic_family_penalty",
            persona_key="gdepar",
            payload={"topic": chosen[:120], "penalty": round(scored[0][2], 2)},
        )
    return chosen


# ─────────────────────────────────────────────────────────────
#  Self-critique: второй проход по готовому посту.
#  Дёшевая «редактура»: ищем клише/штампы/повторы и переписываем при необходимости.
# ─────────────────────────────────────────────────────────────

# Стоп-фразы (включая ранее «выловленные» в обратной связи).
# Если попадается из этого списка — критика обязательна.
_SELFCRITIC_BANNED_PHRASES: dict[str, tuple[str, ...]] = {
    "gdepar": (
        "священнодейств", "братств", "варварств", "обновлённ", "обновленн",
        "загоняй поколен", "выгоняй из себя", "очищение душ", "крестись",
        "взрывная мощь", "вселенн",
        "тишина в парилке", "верхняя полка", "замочи веник на 15",
        "не геройств", "геройствуй", "пульс 140", "пульс выше 140",
        "без фанатизм", "слушай, кириллыч",
    ),
    "stern": (
        "взрывная мощь", "вселенн", "железная дисциплина", "пропуск в мир",
        "сталь в мягкости", "мужская сила", "истинн", "монолитн",
    ),
    "garden": (
        "матушка-земля", "матушк земл", "природа знает лучше",
    ),
    "pension": (
        "@pensiya35", "пенсия в 35", "пенсия 35", "не работать", "финансовая свобода",
    ),
    "lenin": (
        "сим победиши",
        "сим — победиши",
        "парадокс? нет",
        "звучит особенно актуально",
        "революция победила не только",
        "детектив решений",
        "святой миф",
        "ленин vs бюрократ",
        "бюрократ",
        "газет",
        "канцеляр",
        "редакци",
        "типограф",
    ),
}

# Минимальная длина основной части поста (без хэштегов) — если короче,
# почти всегда есть смысл попросить «развернуть».
_SELFCRITIC_MIN_BODY_CHARS = {
    "stern": 700,
    "gdepar": 500,
    "garden": 450,
    "pension": 700,
    "lenin": 500,
}


def _selfcritique_findings(p_key: str, text: str) -> list[str]:
    """Эвристики, после которых имеет смысл звать второй проход LLM."""
    findings: list[str] = []
    if not text:
        return findings

    low = text.lower()
    banned = _SELFCRITIC_BANNED_PHRASES.get(p_key, ())
    for ph in banned:
        if ph in low:
            findings.append(f"запрещённая для персоны фраза: «{ph}»")

    if p_key == "gdepar" and gdepar_content:
        findings.extend(gdepar_content.cliche_findings(text))

    findings.extend(content_p0.p0_findings(text, p_key) if content_p0 else [])

    # Сразу несколько «канцелярских» оборотов.
    for ph in ("в данной статье", "в этой статье", "в этом посте", "дорогие друзья", "уважаемые читатели"):
        if ph in low:
            findings.append(f"мета-обращение: «{ph}»")

    # Совсем короткий пост — обычно «пусто по сути».
    # Считаем тело без последней строки с хэштегами.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    body_lines = [ln for ln in lines if not ln.lstrip().startswith("#")]
    body = "\n".join(body_lines)
    min_len = _SELFCRITIC_MIN_BODY_CHARS.get(p_key, 500)
    if len(body) < min_len:
        findings.append(f"пост слишком короткий: {len(body)} < {min_len} знаков")

    # Повторы целых предложений.
    sents = re.split(r"(?<=[.!?])\s+", body)
    seen: set[str] = set()
    for s in sents:
        key = re.sub(r"[^\wа-яё]+", " ", s.lower()).strip()
        if len(key) > 20 and key in seen:
            findings.append("в посте повторяются целые предложения")
            break
        seen.add(key)

    return findings


async def _selfcritique_rewrite(p_key: str, persona: dict, topic: str, text: str, findings: list[str]) -> str | None:
    """Просим ту же модель переписать пост с учётом замечаний.
    Возвращает новый текст или None, если перезаписать не получилось."""
    if not findings:
        return None
    issues = "\n".join(f"• {f}" for f in findings)
    rewrite_prompt = (
        f"Ты — строгий редактор. Перед тобой готовый пост для Telegram-канала персоны «{p_key}».\n"
        f"ПЕРСОНА: {persona['role']}\n"
        f"ТЕМА: {topic}\n\n"
        f"ПОСТ:\n---\n{text}\n---\n\n"
        f"ПРОБЛЕМЫ В ПОСТЕ:\n{issues}\n\n"
        "ЗАДАЧА: перепиши пост, устранив ВСЕ перечисленные проблемы.\n"
        "ТРЕБОВАНИЯ:\n"
        "• Сохрани заголовок, тон и хэштеги (последняя строка) — но только если они уместны.\n"
        "• Без канцелярита, без обращений «дорогие друзья», без мета-фраз про «в этом посте».\n"
        "• НЕ добавляй секцию «ПРОМПТ:» и английский текст — только русский пост.\n"
        "• Если пост короткий — добавь конкретики (примеры, цифры, простые шаги), не «воды».\n"
        "• Не используй запрещённые для персоны фразы.\n"
        "ВЕРНИ ТОЛЬКО НОВЫЙ ТЕКСТ ПОСТА. Без префиксов «ТЕКСТ:», без комментариев, без markdown-обёрток.\n"
    )
    try:
        status, data = await fetch_llm_response(persona["model"], rewrite_prompt)
        if status != 200 or "choices" not in data:
            return None
        new_text = (data["choices"][0]["message"]["content"] or "").strip()
        # Срезаем возможные «ТЕКСТ:»/«ПРОМПТ:» рудименты.
        new_text = _TEKST_LABEL_BLOCK.sub("", new_text).strip()
        new_text = re.split(rf"(?im)^\s*{_PROMPT_LABEL}\s*:", new_text, maxsplit=1)[0].strip()
        if not new_text or len(new_text) < 100:
            return None
        return new_text
    except Exception as e:
        logger.warning(f"[selfcritique] rewrite error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
#  Авто-публикация по порогу — data/auto_publish.json
# ─────────────────────────────────────────────────────────────

_AUTO_PUBLISH_FILE = "data/auto_publish.json"


def _load_auto_publish_config() -> dict:
    try:
        with open(_AUTO_PUBLISH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "personas": {}}


def _post_body_without_hashtags(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    body = [ln for ln in lines if not ln.lstrip().startswith("#")]
    return "\n".join(body)


# ─────────────────────────────────────────────────────────────
#  Видео-клипы для карточек бань (ВК / Rutube / YouTube / Telegram / mp4)
# ─────────────────────────────────────────────────────────────

def parse_video_clip(url: str) -> dict | None:
    """Распознаёт URL ролика и возвращает структуру для рендера embed.

    Поддерживаемые провайдеры (в порядке приоритета аудитории РФ):
      - VK Video / VK Clips:  vk.com/video-OID_ID, vkvideo.ru/..., /clip-OID_ID
      - Rutube:               rutube.ru/video/HASH/  и  /shorts/HASH/
      - YouTube (бэкап):      youtu.be/ID, youtube.com/watch?v=, /shorts/, /embed/
      - Telegram-пост:        t.me/channel/MSG  (embed-виджет)
      - Прямой файл:          .mp4 | .webm | .mov

    Возвращает None, если URL не распознан.
    """
    if not url:
        return None
    url = url.strip()
    try:
        p = urllib.parse.urlparse(url)
    except Exception:
        return None
    host = (p.hostname or "").lower()
    path = p.path or ""
    qs = urllib.parse.parse_qs(p.query or "")

    # ── VK Video / Clips ─────────────────────────────────────
    if host in {"vk.com", "m.vk.com", "vkvideo.ru", "vk.ru"}:
        m = re.search(r"/(?:video|clip)(-?\d+)_(\d+)", path)
        if m:
            oid, vid = m.group(1), m.group(2)
            embed = f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2"
            h = (qs.get("hash") or [""])[0]
            if h:
                embed += f"&hash={h}"
            return {"provider": "vk", "id": f"{oid}_{vid}", "url": url, "embed_url": embed}
        if "video_ext.php" in path:
            oid = (qs.get("oid") or [""])[0]
            vid = (qs.get("id") or [""])[0]
            if oid and vid:
                embed = f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2"
                h = (qs.get("hash") or [""])[0]
                if h:
                    embed += f"&hash={h}"
                return {"provider": "vk", "id": f"{oid}_{vid}", "url": url, "embed_url": embed}

    # ── Rutube ────────────────────────────────────────────────
    if host.endswith("rutube.ru"):
        m = re.search(r"/(?:video|shorts|play/embed)/([A-Za-z0-9]+)/?", path)
        if m:
            vid = m.group(1)
            return {
                "provider": "rutube",
                "id": vid,
                "url": url,
                "embed_url": f"https://rutube.ru/play/embed/{vid}/",
            }

    # ── YouTube (бэкап) ───────────────────────────────────────
    if host in {"youtu.be"}:
        vid = path.lstrip("/").split("/")[0]
        if vid:
            return {
                "provider": "youtube",
                "id": vid,
                "url": url,
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            }
    if "youtube.com" in host:
        vid = (qs.get("v") or [""])[0]
        if not vid:
            m = re.search(r"/(?:shorts|embed)/([A-Za-z0-9_\-]{6,})", path)
            if m:
                vid = m.group(1)
        if vid:
            return {
                "provider": "youtube",
                "id": vid,
                "url": url,
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            }

    # ── Telegram-пост ─────────────────────────────────────────
    if host in {"t.me", "telegram.me"}:
        m = re.match(r"^/([^/]+)/(\d+)/?$", path)
        if m:
            ch, msg = m.group(1), m.group(2)
            return {
                "provider": "telegram",
                "id": f"{ch}/{msg}",
                "url": url,
                "embed_url": f"https://t.me/{ch}/{msg}?embed=1&dark=1",
            }

    # ── Прямой файл ───────────────────────────────────────────
    if path.lower().endswith((".mp4", ".webm", ".mov", ".m4v")):
        return {"provider": "file", "id": url, "url": url, "embed_url": url}

    return None


def _sanitize_banya_clip_embed_url(raw: object) -> str:
    """Только http(s) или путь от корня без //… (без protocol-relative и чужих схем)."""
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if s.startswith(("https://", "http://")):
        return s
    if s.startswith("/") and not s.startswith("//"):
        return s
    return ""


def normalize_clip_list(raw) -> list[dict]:
    """Приводит сохранённый clips_json к списку dict'ов с провайдерами.

    Старые записи могли быть просто строками — мигрируем «на лету».
    После нормализации `embed_url` режется до безопасных значений (см. `_sanitize_banya_clip_embed_url`).
    """
    out: list[dict] = []
    if not raw:
        return out
    try:
        data = raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        return out
    for item in data or []:
        if isinstance(item, dict) and item.get("embed_url"):
            out.append(item)
        elif isinstance(item, str):
            parsed = parse_video_clip(item)
            if parsed:
                out.append(parsed)
            else:
                out.append({"provider": "file", "id": item, "url": item, "embed_url": item})
    for d in out:
        if isinstance(d, dict):
            d["embed_url"] = _sanitize_banya_clip_embed_url(d.get("embed_url"))
    return out


def _auto_publish_rules_for(cfg: dict, p_key: str, topic_raw: str) -> tuple[dict, dict]:
    """(rules, rubric_cfg) — rubric_cfg не пустой, если сработала рубрика."""
    rubrics = cfg.get("rubrics") or {}
    topic = topic_raw or ""
    for _name, rcfg in rubrics.items():
        if not isinstance(rcfg, dict) or not rcfg.get("enabled"):
            continue
        personas = rcfg.get("personas") or [p_key]
        if p_key not in personas:
            continue
        markers = rcfg.get("topic_markers") or []
        if markers and not any(m in topic for m in markers):
            continue
        defs = cfg.get("defaults") or {}
        rules = {**defs, **{k: v for k, v in rcfg.items() if k not in ("enabled", "personas", "topic_markers")}}
        return rules, rcfg
    defs = cfg.get("defaults") or {}
    per = (cfg.get("personas") or {}).get(p_key) or {}
    return {**defs, **per}, {}


def _auto_publish_reason_blocked(
    cfg: dict,
    p_key: str,
    text: str,
    img_f: str | None,
    draft: PostDraft,
    *,
    topic_raw: str = "",
    rules_override: dict | None = None,
) -> str | None:
    """None — можно авто-опубликовать; иначе причина для лога."""
    rules = rules_override
    if rules is None:
        if not cfg.get("enabled"):
            return "cfg.disabled"
        per = (cfg.get("personas") or {}).get(p_key) or {}
        if not per.get("enabled"):
            return "persona.disabled"
        defs = cfg.get("defaults") or {}
        rules = {**defs, **per}
    else:
        if not rules:
            return "rubric.disabled"
    targets = PLATFORM_TARGETS.get(p_key, {})
    if not targets.get("tg"):
        return "no_tg_target"
    if not text or text.startswith("🛑") or "Ошибка ИИ" in text or text.startswith("Ошибка"):
        return "bad_text"
    p0 = content_p0.p0_findings(text, p_key) if content_p0 else []
    if p0:
        return f"p0:{p0[0][:60]}"
    if rules.get("require_video"):
        if not _is_video_path(img_f) or not os.path.exists(img_f):
            return "no_video"
    elif rules.get("require_image", True) and (not img_f or not os.path.exists(img_f)):
        return "no_image"
    if rules.get("require_zero_regen", True) and (draft.regen_count or 0) > 0:
        return "regen>0"
    if rules.get("require_zero_badimg", True) and (draft.bad_image_count or 0) > 0:
        return "badimg>0"
    max_issues = int(rules.get("max_selfcrit_issues", 0))
    if max_issues < 99:
        findings = _selfcritique_findings(p_key, text)
        if len(findings) > max_issues:
            return f"selfcrit:{len(findings)}"
    min_chars = int(rules.get("min_body_chars", 400))
    if not rules.get("skip_body_floor"):
        floor = int(_SELFCRITIC_MIN_BODY_CHARS.get(p_key, 400))
        min_chars = max(min_chars, floor)
    body = _post_body_without_hashtags(text)
    if len(body) < min_chars:
        return f"short:{len(body)}<{min_chars}"
    return None


def _publish_error_hint(exc: Exception, *, persona_key: str, tg_target: str | None) -> str:
    """Короткая подсказка для алерта админу (без сырого Telegram API)."""
    raw = str(exc).lower()
    channel = tg_target or "канал"
    if "not a member of the channel" in raw or "chat not found" in raw and persona_key == "pension":
        return (
            "Бот не добавлен в канал «На пенсию… НИКОГДА!» (@pensiya_nikogda).\n"
            "Канал → Управление → Администраторы → добавьте бота, который присылает "
            "вам черновики, с правом «Публикация сообщений»."
        )
    if "not enough rights" in raw or "need administrator rights" in raw:
        return (
            f"У бота нет прав публиковать в {channel}.\n"
            "Добавьте бота администратором с правом публикации постов."
        )
    if "can't parse entities" in raw or "unmatched end tag" in raw:
        return "Ошибка HTML в тексте поста. Отклоните черновик и пересоздайте из Obsidian."
    if "chat not found" in raw:
        return (
            f"Канал не найден ({channel}). Проверьте PENSION_TG_CHAT_ID в .env "
            "и что бот добавлен в канал."
        )
    if "forbidden" in raw:
        return (
            f"Telegram отклонил публикацию в {channel}. "
            "Проверьте, что бот — админ канала с правом постинга."
        )
    return "Повторите позже или проверьте логи empire_main на VPS."


def _is_video_path(path: str | None) -> bool:
    if not path:
        return False
    return path.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".m4v"))


async def _send_draft_to_channel(draft: PostDraft) -> tuple[bool, str | None, int | None]:
    """Отправить черновик в целевой Telegram-канал. (ok, error_hint, message_id)."""
    targets = _platform_targets().get(draft.persona_key, {})
    tg_id = targets.get("tg")
    if not tg_id:
        hint = (
            "Не задан канал для публикации (PENSION_TG_CHAT_ID или PENSION_TG_URL)."
            if draft.persona_key == "pension"
            else f"Нет chat_id для persona={draft.persona_key}."
        )
        logger.warning("[publish] no tg target %s", draft.persona_key)
        return False, hint, None
    text = draft.text_content or ""
    path = draft.image_path
    cap_limit = 1024 if draft.persona_key == "stern" else 1000
    try:
        message_id: int | None = None
        if path and os.path.exists(path) and _is_video_path(path):
            caption, continuation = _admin_caption_for_photo(text, max_len=cap_limit)
            msg = await bot.send_video(
                tg_id, video=FSInputFile(path), caption=caption, parse_mode="HTML"
            )
            message_id = msg.message_id
            if continuation:
                await bot.send_message(tg_id, continuation, parse_mode="HTML")
        elif path and os.path.exists(path):
            caption, continuation = _admin_caption_for_photo(text, max_len=cap_limit)
            msg = await bot.send_photo(
                tg_id, photo=FSInputFile(path), caption=caption, parse_mode="HTML"
            )
            message_id = msg.message_id
            if continuation:
                await bot.send_message(tg_id, continuation, parse_mode="HTML")
        else:
            msg = await bot.send_message(tg_id, text, parse_mode="HTML")
            message_id = msg.message_id
        return True, None, message_id
    except Exception as e:
        logger.warning(f"[publish] channel send failed {draft.persona_key}: {e}")
        return False, _publish_error_hint(e, persona_key=draft.persona_key, tg_target=tg_id), None


async def _try_auto_publish_scheduled(
    d_id: int, p_key: str, text: str, img_f: str | None, *, topic_raw: str = ""
) -> bool:
    """Только для постов из расписания. True если ушло в канал без модерации."""
    cfg = _load_auto_publish_config()
    rules, rubric = _auto_publish_rules_for(cfg, p_key, topic_raw)
    if not cfg.get("enabled") and not rubric:
        return False
    async with async_session() as session:
        draft = await session.get(PostDraft, d_id)
        if not draft:
            return False
        if not rubric:
            per = (cfg.get("personas") or {}).get(p_key) or {}
            if not per.get("enabled"):
                return False
        reason = _auto_publish_reason_blocked(
            cfg, p_key, text, img_f, draft, rules_override=rules if rubric else None
        )
        if reason:
            logger.info(f"[autopublish] skip #{d_id} {p_key}: {reason}")
            return False
        ok, _err, msg_id = await _send_draft_to_channel(draft)
        if not ok:
            return False
        draft.status = "published"
        draft.decision = "auto"
        draft.decided_at = datetime.utcnow()
        await session.commit()
        await _publish_extra_channels(draft)
        if p_key == "stern" and msg_id:
            import stern_week_arc as swa

            swa.mark_post_published(d_id, msg_id)
        _record_stern_technique_if_published(draft)
        _record_stern_comic_if_published(draft)
    logger.info(f"[autopublish] published #{d_id} {p_key} to channel")
    return True


async def _notify_admin_auto_compact(
    d_id: int, p_key: str, topic: str, text: str, cfg: dict
) -> None:
    if not cfg.get("notify_admin_compact", True):
        return
    snippet = (text or "").replace("\n", " ").strip()
    if len(snippet) > 220:
        snippet = snippet[:220] + "…"
    await bot.send_message(
        ADMIN_ID,
        "✅ <b>Авто-опубликовано</b> в канал\n"
        f"#{d_id} · <code>{html_std.escape(p_key)}</code>\n"
        f"📝 {html_std.escape((topic or '')[:140])}\n\n"
        f"<i>{html_std.escape(snippet)}</i>",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────
#  Запуск скаута: не чаще раза в час (по mtime файла), внутри event loop.
# ─────────────────────────────────────────────────────────────

_SCOUT_TRENDS_FILE = "data/current_trends.json"
_SCOUT_LOCK = asyncio.Lock()


async def _refresh_scout_if_stale(max_age_sec: int = 3600) -> bool:
    """Если data/current_trends.json старше max_age_sec — перезапускаем scout.py.
    Возвращает True, если файл фактически обновился."""
    try:
        age = time.time() - os.path.getmtime(_SCOUT_TRENDS_FILE)
    except OSError:
        age = float("inf")
    if age < max_age_sec:
        return False
    async with _SCOUT_LOCK:
        # Перепроверяем под локом, чтобы не запускать дважды.
        try:
            age = time.time() - os.path.getmtime(_SCOUT_TRENDS_FILE)
            if age < max_age_sec:
                return False
        except OSError:
            pass
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "scout.py",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=60)
            logger.info("[scout] refreshed")
            return True
        except Exception as e:
            logger.warning(f"[scout] refresh error: {e}")
            return False


async def _resolve_slot_topic(p_key: str, slot_value) -> str:
    """Разрешить значение слота расписания в итоговую строку темы для LLM."""
    topic, _, _, _ = await _resolve_scheduled_slot(p_key, slot_value)
    return topic


async def _resolve_scheduled_slot(
    p_key: str,
    slot_value,
    *,
    when: datetime | None = None,
) -> tuple[str, str | None, str | None, dict | None]:
    """(topic_raw, prebuilt_text, prebuilt_image, rubric_seed). prebuilt — без LLM."""
    when = when or msk_now()
    weekday = when.weekday()
    if isinstance(slot_value, dict) and slot_value.get("type") == "spy_inspired":
        if p_key in ("gdepar", "stern"):
            async with async_session() as session:
                topic = await __import__("spy_inspired").resolve_spy_inspired_topic(session, p_key)
            return topic, None, None, None
    if p_key == "pension" and pension_content:
        feed = pension_content.is_raw_news_slot(slot_value)
        if feed:
            async with async_session() as session:
                t, b = await pension_content.build_raw_news_prebuilt(session, feed)
                return t, b, None, None
    if p_key == "gdepar" and gdepar_content:
        t, pb, img = await gdepar_content.resolve_gdepar_slot(
            slot_value, resolve_topic_fn=_resolve_slot_topic_plain
        )
        return t, pb, img, None
    if p_key == "lenin" and lenin_content:
        recent_lenin = await _recent_post_bodies("lenin", days=28, limit=12)
        return await lenin_content.resolve_lenin_slot(
            slot_value, weekday=weekday, recent_bodies=recent_lenin
        )
    if p_key == "stern" and stern_content:
        return await stern_content.resolve_stern_slot(
            slot_value, weekday=weekday, resolve_topic_fn=_resolve_slot_topic_plain
        )
    if p_key == "garden" and garden_content:
        t, pb, img = await garden_content.resolve_garden_slot(
            slot_value, resolve_topic_fn=_resolve_slot_topic_plain
        )
        return t, pb, img, None
    return await _resolve_slot_topic_plain(p_key, slot_value), None, None, None


async def _resolve_slot_topic_plain(p_key: str, slot_value) -> str:
    default_topic = "Свободная тема"
    if slot_value is None:
        return default_topic
    if isinstance(slot_value, dict) and (slot_value.get("type") or slot_value.get("special")):
        return default_topic
    variants = _slot_variants_from_value(slot_value)
    if variants is None:
        s = str(slot_value).strip()
        return s if s else default_topic
    if not variants:
        return default_topic
    if len(variants) == 1:
        return variants[0]
    return await _pick_least_similar_variant(p_key, variants)


async def generate_draft_content(p_key, topic_raw, *, rubric_seed: dict | None = None):
    persona = PERSONAS[p_key]
    calendar_seed = (
        rubric_seed if (rubric_seed or {}).get("_kind") == "lenin_calendar" else None
    )
    stern_week_seed = (
        rubric_seed
        if p_key == "stern"
        and (rubric_seed or {}).get("_kind", "").startswith("stern_weekly")
        else None
    )
    topic_rules = (
        "СТИЛЬ КАК В ЖИВОМ TELEGRAM-КАНАЛЕ:\n"
        "• Сильный заголовок (можно с одним уместным эмодзи в начале).\n"
        "• Дальше — связный текст короткими абзацами через пустую строку, без канцелярита и без «воды».\n"
        "• НЕ дублируй рубрику и хэштеги в начале поста.\n"
        "• Без служебных блоков: не пиши «ТЕКСТ:», не вставляй английский промпт, не разделители ---, не секцию ПРОМПТ внутри поста.\n"
        "• Последняя строка поста (перед отдельной строкой с @) — ТОЛЬКО хэштеги через пробел: 4–7 штук на русском, слитно (#слово).\n"
    )

    topic = topic_raw
    rubric_plain: str | None = None
    match_rubric = re.match(r"\[(.*?)\]\s*(.*)", topic_raw)
    if match_rubric:
        rubric_plain = match_rubric.group(1).strip()
        topic = match_rubric.group(2).strip()

    if calendar_seed and p_key == "lenin" and lenin_content:
        topic_rules += lenin_content.calendar_prompt_block(calendar_seed)
        topic = calendar_seed.get("topic") or topic_raw
    elif stern_week_seed:
        import stern_week_arc as swa

        kind = stern_week_seed.get("_kind")
        if kind == "stern_weekly_plan":
            topic_rules += swa.weekly_plan_prompt_block()
            topic_rules += (
                "\nОБЪЁМ программы: 900–1400 знаков (без хэштегов).\n"
                "СТРУКТУРА (строго, каждая строка с новой строки):\n"
                "  Пн: …\n  Вт: …\n  Ср: …\n  Чт: …\n  Пт: …\n  Сб: …\n  Вс: отдых / лёгкая рутина\n"
                "  Тест недели: [название] — [метрика, среда, норма/хорошо/отлично с цифрами]\n"
                "Картинка не нужна — в ПРОМПТ напиши одно слово: skip\n"
            )
        elif kind == "stern_weekly_test":
            topic_rules += swa.weekly_test_prompt_block(swa.get_current_plan_text())
            topic_rules += (
                "\nОБЪЁМ: 700–1100 знаков. Без нового теста, только из плана пн.\n"
                "Секции: зачем → как выполнять (1-2-3) → нормы (3 строки с цифрами).\n"
                "Картинка не нужна — в ПРОМПТ: skip\n"
            )
    elif rubric_seed:
        extra = ""
        if p_key == "lenin" and lenin_content:
            extra = lenin_content.rubric_expansion_rules()
        elif p_key == "stern" and stern_content:
            extra = stern_content.rubric_expansion_rules()
        if rubric_seed.get("rubric_key") == "athletic_legacy":
            import stern_athletic_legacy as sal

            topic_rules += sal.expansion_prompt_block(rubric_seed, extra_rules=extra)
        else:
            topic_rules += rubric_posts.rubric_expansion_prompt_block(rubric_seed, extra_rules=extra)

    topic_lower = topic_raw.lower()
    is_pension_video = p_key == "pension" and (
        "[видео]" in topic_lower
        or "новое видео" in topic_lower
        or "новый выпуск" in topic_lower
        or "youtube" in topic_lower
    )

    topic_rules += f"Пиши на тему: {topic}. "

    if "[spy_inspired]" in (topic_raw or "").lower():
        topic_rules += (
            "\nРЕЖИМ «РАЗВЕДКА»: в теме слота — мотив взлётного поста конкурента. "
            "Напиши НОВЫЙ пост: другой заход, наш тон, без копипаста и без названия чужого канала.\n"
        )

    # Память тем: если похожая тема уже была — заставляем взять новый ракурс.
    history_hint = await _topic_history_hint(p_key, topic_raw)
    if history_hint:
        topic_rules += "\n" + history_hint

    recent_bodies: list[str] = []
    if p_key == "gdepar" and gdepar_content:
        recent_bodies = await _recent_post_bodies("gdepar", days=21, limit=15)
        mem = gdepar_content.bodies_memory_hint(recent_bodies)
        if mem:
            topic_rules += mem

    recent_lenin_bodies: list[str] = []
    if p_key == "lenin" and lenin_content:
        recent_lenin_bodies = await _recent_post_bodies("lenin", days=28, limit=12)
        mem = lenin_content.bodies_memory_hint(recent_lenin_bodies)
        if mem:
            topic_rules += mem

    now = datetime.now(MSK_TZ)
    month_idx = now.month
    months = ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    seasons = {12: "зима", 1: "зима", 2: "зима", 3: "весна", 4: "весна", 5: "весна", 6: "лето", 7: "лето", 8: "лето", 9: "осень", 10: "осень", 11: "осень"}
    current_season = seasons[month_idx]

    if p_key == "garden":
        topic_rules += f"\nСЕЗОННОСТЬ СТРОГО: Сейчас месяц {months[month_idx]} ({current_season}). Все советы должны быть строго актуальны для ЭТОГО времени года в средней полосе РФ!\n"
        topic_rules += (
            "ОТСТРОЙКА (docs/garden_positioning.md): не как массовые огородные блоги — без «100 советов», "
            "«суперурожай за 3 дня», «матушка-земля», рекламы удобрений. Дай 1–2 конкретных действия и "
            "полевой тест «как проверить на грядке за минуту» (руки/запах/глубина влаги). "
            "Можно коротко: «так пишут все / здесь иначе» — без высокомерия.\n"
        )
        topic_rules += (
            "Картинка генерируется ОТДЕЛЬНО от текста: в секции ПРОМПТ опиши ТОЛЬКО кадр для обложки "
            "(без деда Степаныча): крупный план предмета/сцены из поста, по сезону.\n"
            "ВАЖНО ДЛЯ ПРОМПТА (английский): обязательно укажи стадию растения, актуальную для "
            f"{months[month_idx]} в средней полосе РФ (rassada/seedlings/just transplanted/flowering/"
            "early fruits/harvest — в зависимости от месяца). Не используй фразы 'ripe red tomatoes' "
            "если речь о мае; для томатов в мае: 'young tomato seedlings about 20-30 cm tall, "
            "just transplanted into the open ground, no fruits yet'.\n"
        )

    if p_key == "stern" and not stern_week_seed:
        prog_num = get_and_increment_stern_counter()
        # Конкретное упражнение vs. широкая рубрика (рутина/разминка/мобильность/психология)
        is_exercise_topic = bool(re.search(
            r"(?i)(рывок|толчок|мах|тяга|жим|присед|отжимани|подтягиван|"
            r"планка|становая|выпад|приседан|swing|snatch|clean|jerk|deadlift|"
            r"squat|press|push[\s-]?up|pull[\s-]?up|row|карри|carry|"
            r"турецк|getup|get[\s-]?up|bird[\s-]?dog|птиц[а-я]*[\s\-–]*собак)",
            topic,
        ))
        is_routine_topic = bool(re.search(
            r"(?i)(рутин|разминк|гимнастик|растяжк|мобильн|подвижн|"
            r"восстановлен|массажн|МФР|вакуум|дыхан|осанк|сон|кортизол|"
            r"мотивац|психолог|выгоран|срыв|питани|диет|долголет|после\s*40)",
            topic,
        ))

        common_rules = (
            f"\nЗАДАЧА: материал в духе программы / рубрики (внутренний номер для себя: {prog_num}), "
            "подача — авторский канал, не ГОСТ.\n"
            "ОБЪЁМ: 1100–1700 знаков основного текста (без заголовка и хэштегов).\n"
            "СЛОВАРЬ:\n"
            "  • «кор» — мышцы корпуса, мужской род. Пиши: «кор работает», «активация кора», «жёсткий кор». "
            "  НЕЛЬЗЯ: «Кора играет», «кора удерживает» — это про дерево, не про мышцы.\n"
            "  • «гиря» склоняется правильно: гиря, гири, гире, гирю, гирей; во мн. числе — гири, гирь, гирям, гирями. "
            "  НЕЛЬЗЯ: «гира», «гиры», «гиру», «гирой».\n"
            "Не использовать сплошной текст одним абзацем, не использовать ### в подзаголовках. "
            "Опирайся на источники из базы знаний (Цацулин, Тсатсулин, МакГилл) и цитируй цифры/диапазоны.\n"
            "ОБЯЗАТЕЛЬНО: в тексте — минимум одна явная отсылка к источнику из БАЗЫ ЗНАНИЙ "
            "(фамилия + смысл/цифра). Без опоры на базу пост считается браком.\n"
            "ЗАПРЕТ: соревновательный «гиревой спорт» (разряды, помост, биатлон, нормативы ВФГС/WKSF), "
            "если тема слота не про историю снаряда.\n"
            "Картинка — отдельно: в ПРОМПТ только английское описание кадра по теме поста.\n"
        )

        if is_exercise_topic:
            topic_rules += common_rules + (
                "РЕЖИМ «УПРАЖНЕНИЕ» — ФОРМАТИРОВАНИЕ СТРОГО:\n"
                "  • заголовок поста — обычная строка с одним уместным эмодзи (без **звёзд**);\n"
                "  • далее ЧЕТЫРЕ секции, КАЖДАЯ с СВОИМ жирным подзаголовком на отдельной строке "
                "    через **двойные звёздочки** (превратятся в <b>), в такой последовательности:\n"
                "      **Анатомия движения**\n"
                "      **Техника шаг за шагом**\n"
                "      **3 ошибки новичков**\n"
                "      **Прогрессия и безопасность**\n"
                "  • между секциями — ОДНА пустая строка;\n"
                "  • «Анатомия движения» — 1 связный абзац (мышцы, нейтральный таз, роль кора по МакГиллу);\n"
                "  • «Техника» — нумерованный список 1)…4) (старт → разгон → верхняя точка → возврат), "
                "    отдельной строкой после списка — фраза про дыхание и темп;\n"
                "  • «3 ошибки новичков» — три буллета через `• ` (точка + пробел) по 1–2 предложения;\n"
                "  • «Прогрессия и безопасность» — 2–4 строки: стартовый вес, диапазон повторов, когда "
                "    добавлять, противопоказания.\n"
            )
        elif is_routine_topic:
            topic_rules += common_rules + (
                "РЕЖИМ «РУТИНА/РАЗМИНКА/ОБЗОР» — структура НЕ как для упражнения, а живой авторский пост:\n"
                "  • короткий заголовок (с одним эмодзи);\n"
                "  • 1 абзац — зачем это и кому особенно нужно (1–2 факта/цифры);\n"
                "  • КОНКРЕТНЫЙ комплекс/чек-лист: 4–7 пунктов нумерованным или маркированным списком, "
                "    каждый пункт — что именно делать (с числом повторов, секундами, амплитудой). "
                "    НЕ пиши «выполняйте круговые движения в суставах» вообще — пиши «5 кругов плечами "
                "    вперёд и назад, 10 наклонов таза, 8 приседаний на пятки и т.д.»;\n"
                "  • 2–3 строки — частые ошибки и сигналы, когда стоит остановиться;\n"
                "  • 1–2 строки — частота / встроенность в день (утром / перед тренировкой / каждый час).\n"
                "ЗАПРЕЩЕНЫ подзаголовки **Анатомия движения** / **Техника шаг за шагом** / "
                "**3 ошибки новичков** / **Прогрессия и безопасность** — это не упражнение.\n"
            )
        else:
            topic_rules += common_rules + (
                "РЕЖИМ «СВОБОДНЫЙ»: один заголовок, 3–5 коротких абзацев. Конкретика, цифры, выводы. "
                "Без обязательных жирных подзаголовков.\n"
            )

    if p_key == "pension" and is_pension_video:
        topic_rules += (
            "\nРЕЖИМ «НОВОЕ ВИДЕО»: разогрев, интрига, о чём выпуск буллетами (коротко). "
            "НЕ вставляй вручную ссылки на YouTube/VK/Rutube и блоки P.S. — они будут добавлены системой под твоим текстом. "
            "Не дублируй финальную строку хэштегов — сгенерируй её один раз в конце ТЕКСТа.\n"
            "ЗАПРЕТ: не упоминай 'На пенсию в 35', @pensiya35, Бабайкина и любые их каналы/книги.\n"
        )
    elif p_key == "pension":
        if pension_content and topic_raw.strip().upper().startswith("[ANALYSIS]"):
            picked = pension_content.parse_voices_from_topic(topic_raw)
            topic_rules += pension_content.voice_prompt_block(picked or None)
        topic_rules += (
            "\nРЕЖИМ «БЕЗ ВИДЕО»: авторский разбор, длинный связный пост (не меньше 1400 знаков).\n"
            "СТРУКТУРА:\n"
            "  • короткая зацепка (1–2 строки, проблема или новость дня);\n"
            "  • 2–3 содержательных тезиса, каждый — с фактом или цитатой из БАЗЫ ЗНАНИЙ "
            "    (Талеб, Хулиномика, Капитал и т.п.); авторов называй по фамилии, а не по [n];\n"
            "  • контрпример или типовая ошибка инвестора;\n"
            "  • практический вывод на 2–3 строки.\n"
            "ЗАПРЕТЫ:\n"
            "  • не пересказывай 'мою стратегию', 'мой портфель' и любые личные тексты канала как факт; "
            "    'личная стратегия' допустима только как контекст тона, без формулировок 'как у [n]';\n"
            "  • не упоминай 'На пенсию в 35', @pensiya35, Бабайкина и его книги/каналы — это конкурент;\n"
            "  • никаких 'фишек антихрупкости', 'ржавеют слабые звенья', 'денежных ручейков' — пиши без штампов.\n"
        )

    if p_key == "gdepar":
        topic_rules += (
            "\nТон Михалыча: разговорный, по делу, чуть с подначкой. "
            "СТОП-СЛОВА (ни разу за пост): 'священнодействие', 'братство', 'равенство', 'варварство', "
            "'обновлённый', 'душа', 'загоняй поколения', 'крестись', 'выгоняй из себя', 'хрень'. "
            "Не делай морализаторских выводов и философских концовок. Никаких 'выходишь обновлённым'. "
            "Запрещены лекции: «не геройствуй», «пульс 140 — выходи», «слушай, Кириллыч».\n"
            "НЕ начинай с шаблона «Кириллыч, слушай/смотри» — допустим диалог <b>Михалыч:</b> / <b>Кириллыч:</b>.\n"
            "АНТИ-КЛИШЕ (не повторяй, если тема не про это напрямую): «тишина в парилке» как главный тезис; "
            "совет «лезь на верхнюю полку»; «замочи веник на 15 минут»; связка алкоголь+давление+сердце в одном посте.\n"
            "Что должно быть в посте: конкретика по ТЕМЕ слота — инженерия, рецепт, история, литература и т.д. "
            "Не размазывай универсальный чек-лист «температура, 2–3 захода, веник» в каждый пост.\n"
            "В ПРОМПТ — только английское описание атмосферы бани/пара по смыслу поста. "
            "Если пост про веник (рубрика [Веники], берёза/дуб/запаривание) — в ПРОМПТ достаточно "
            "одной фразы birch venik или oak venik; система подставит проверенный шаблон кадра. "
            "ЗАПРЕЩЕНО в промпте: 'broom', 'sweeping broom', 'straw broom', 'household broom', 'witch broom'.\n"
        )
        if gdepar_content:
            lit_block = gdepar_content.literature_prompt_block(topic_raw)
            if lit_block:
                topic_rules += lit_block
            health_block = gdepar_content.health_topic_prompt_block(topic_raw)
            if health_block:
                topic_rules += health_block
            bayka_block = gdepar_content.bayka_prompt_block(topic_raw)
            if bayka_block:
                topic_rules += bayka_block
            duo_block = gdepar_content.duo_dialog_prompt_block(topic_raw)
            if duo_block:
                topic_rules += duo_block
            banya_week_block = gdepar_content.banya_week_prompt_block(topic_raw)
            if banya_week_block:
                topic_rules += banya_week_block

    lenin_event = None
    book_chunk = None

    if p_key == "lenin":
        topic_rules += (
            "\nПРАВИЛО ЦИТАТ: прямая цитата Ленина — с источником (В.И. Ленин, ПСС, т. N, стр. M). "
            "Без редакторских комментариев вроде «детектив решений», «святой миф», «парадокс? нет», "
            "«актуально сегодня». Не начинай с «🔥 Ленин vs …» и не повторяй сюжет «Сим победиши» "
            "и бюрократии 1921 года, если он уже был в недавних постах.\n"
            "ЗАПРЕТ СЮЖЕТОВ (если не тема слота дословно): газеты, редакции, типографии, "
            "канцелярия, «чиновник с папкой», бюрократия как главный герой поста.\n"
            "ЖЁСТКИЙ ЗАПРЕТ (не использовать никогда, даже если попало в базу): письмо в «Невскую Звезду», "
            "полемика в газетах, «издания теряют читателей», «нужно больше актуальных вопросов и обсуждений в газетах» — "
            "это избитый сюжет, подписчики его уже видели.\n"
            "Структура: факт/цитата из БАЗЫ → краткий контекст (кто, когда, к чему) → один вывод в 1–2 строки. "
            "Без пафоса и без «революция победила не только на баррикадах».\n"
        )
        if lenin_content.recent_had_press_story(recent_lenin_bodies):
            topic_rules += (
                "\nВ недавних постах уже был сюжет про прессу/полемику — возьми ДРУГОЙ фрагмент из базы "
                "(другой год, тема, том ПСС). Не «Невская Звезда», не «сухие газеты».\n"
            )
        topic_rules += "В ПРОМПТ — только английское описание исторического визуала/архива к теме поста.\n"

        topic_lower = topic.lower()
        if calendar_seed:
            lenin_event = calendar_seed.get("event_line")
        elif "календарь" in topic_lower or "в этот день" in topic_lower or "вэтотдень" in topic_lower:
            lenin_event = get_lenin_calendar_event()
            if lenin_event:
                match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})\s*[—\-]\s*(.*)", lenin_event)
                if match:
                    d, m, y, event_desc = match.groups()
                    old_date = calculate_old_style(int(d), int(m), int(y))
                    topic_rules += f"ФАКТ ИЗ БАЗЫ: {lenin_event}\nДАННЫЕ ДЛЯ ШАБЛОНА: Старый стиль = {old_date}, Год = {y}.\n"
                    topic_rules += (
                        "НАЧАЛО ПОСТА: Ты ОБЯЗАН начать текст СТРОГО с фразы:\n"
                        f"«В этот день (по старому календарю {old_date}) {y} года [органично впиши событие с глаголом].»\n"
                        "Далее с нового абзаца дай исторический анализ."
                    )
        elif "чтение ленинианы" in topic_lower or "сказка" in topic_lower:
            book_chunk = get_lenin_book_chunk()
            if book_chunk:
                topic_rules += f"СТРОГОЕ ПРАВИЛО: Отрывок из книги ({book_chunk['source']}). Сделай революционное вступление и приведи текст без искажений:\n\n{book_chunk['text']}"

    kb_content = ""
    load_kb = not book_chunk and (not rubric_seed or calendar_seed)
    if load_kb:
        db_path = f"vector_db/{p_key}"
        if os.path.exists(db_path) and embeddings is not None:
            try:
                db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
                if p_key == "lenin":
                    k_docs = 8
                elif p_key == "pension":
                    k_docs = 10
                else:
                    k_docs = 5
                kb_query = topic
                if calendar_seed:
                    kb_query = calendar_seed.get("rag_query") or topic
                raw_docs = db.similarity_search(kb_query, k=k_docs * 2)
                if p_key == "lenin" and lenin_content:
                    raw_docs = lenin_content.filter_lenin_kb_docs(
                        raw_docs, recent_lenin_bodies
                    )
                if p_key == "pension":
                    # Личные тексты канала (my_strategy.txt / style_author.txt) идут как тон,
                    # а не как факты: убираем их из фактологической базы знаний.
                    raw_docs = [d for d in raw_docs if d.metadata.get("kind") != "txt"]
                    raw_docs = [
                        d for d in raw_docs
                        if "scripts/" not in str(d.metadata.get("source", ""))
                        and "reference/" not in str(d.metadata.get("source", ""))
                    ]
                docs = raw_docs[:k_docs]
                kb_lines: list[str] = []
                for i, d in enumerate(docs, 1):
                    src = d.metadata.get("source", "?")
                    pages = d.metadata.get("pages")
                    line_no = d.metadata.get("line")
                    head = f"[{i}] Источник: {src}"
                    if pages:
                        head += f", стр. {pages}"
                    elif line_no is not None:
                        head += f", календарь строка {line_no}"
                    kb_lines.append(f"{head}\n{d.page_content}")
                kb_content = "\n\n".join(kb_lines)
            except Exception:
                pass

    kb_limit = 8000 if p_key in ("lenin", "pension") else 4000

    scout_data_str = ""
    try:
        with open("data/current_trends.json", "r", encoding="utf-8") as f:
            scout_data = json.load(f)
    except Exception:
        scout_data = {}

    if p_key == "pension":
        f_news = "\n".join(scout_data.get("financial_news", []))
        p_news = "\n".join(scout_data.get("politics_news", []))
        if f_news or p_news:
            scout_data_str = f"ФИНАНСЫ ЗА 3 ДНЯ:\n{f_news}\n\nОБЩЕСТВО И ПОЛИТИКА:\n{p_news}"
    elif not rubric_seed and p_key in ("gdepar", "garden", "lenin"):
        persona_topics = scout_data.get("topics", {}).get(p_key, [])
        if persona_topics:
            header = {
                "gdepar": "СВЕЖИЕ ПОВОДЫ ИЗ НОВОСТЕЙ (за 3 дня), используй как фон, но не пересказывай:",
                "garden": "СВЕЖИЕ ПОВОДЫ ИЗ НОВОСТЕЙ (за 3 дня), используй как фон, но не пересказывай:",
                "lenin":  "СВЕЖИЕ ПОВОДЫ ИЗ НОВОСТЕЙ (за 3 дня) — основа для марксистского анализа:",
            }[p_key]
            scout_data_str = header + "\n" + "\n".join(persona_topics[:8])

    if rubric_plain:
        rtag = _hashtag_from_rubric(rubric_plain)
        if rtag:
            topic_rules += f"\nРУБРИКА (для хэштегов): первый тег в финальной строке обязан быть {rtag}.\n"

    response_format = (
        "ОТВЕТЬ СТРОГО В ДВУХ БЛОКАХ. ОБА БЛОКА ОБЯЗАТЕЛЬНЫ, КАЖДЫЙ С СОБСТВЕННЫМ ЗАГОЛОВКОМ "
        "НА ОТДЕЛЬНОЙ СТРОКЕ. ЗАГОЛОВКИ — РОВНО ТАКИЕ, БЕЗ markdown-обёрток "
        "(никаких **ТЕКСТ:**, ### ПРОМПТ: и т.п.):\n\n"
        "ТЕКСТ:\n"
        "[Готовый пост для канала: только то, что увидит подписчик. Без английского промпта внутри. "
        "ВАЖНО: НЕ оставляй в финальном тексте служебные маркеры цитирования [1], [2], [3-5] и т.п. — "
        "они только для внутренних рассуждений, в публикации их быть не должно. "
        "Если упоминаешь конкретные коммерческие препараты/бренды, добавляй фразу «или аналоги», "
        "«или подобные», «и схожие средства» — не выставляй один бренд как единственный вариант. "
        "Последняя строка этого блока — только хэштеги через пробел.]\n\n"
        "ПРОМПТ:\n"
        "[Только английский промпт для генерации обложки: 1–3 коротких предложения, кратко, визуально, "
        "без русского текста и без цитат из поста. Картинка иллюстрирует суть; при перегенерации "
        "картинки этот блок не попадёт в пост.]\n\n"
        "КРИТИЧНО: перед английским описанием обязана быть строка ровно `ПРОМПТ:` (по-русски, без звёздочек). "
        "Если ты выдашь английский абзац без заголовка ПРОМПТ: — это ошибка формата."
    )

    user_prompt = (
        f"ИНСТРУКЦИЯ: {persona['role']}\n"
        f"ПРАВИЛА: {topic_rules}\n"
        f"{scout_data_str}\n"
        f"БАЗА ЗНАНИЙ (цитируй по номеру источника [n], не выдумывай страницы):\n{kb_content[:kb_limit]}\n\n"
        f"{response_format}"
    )

    llm_temp = 0.55 if p_key == "gdepar" else 0.2
    try:
        status, data = await fetch_llm_response(persona["model"], user_prompt, temperature=llm_temp)
        if status != 200 or "choices" not in data:
            err_detail = data.get("error") if isinstance(data, dict) else data
            if isinstance(err_detail, dict):
                err_detail = err_detail.get("message") or err_detail.get("code") or str(err_detail)
            return (
                f"🛑 Ошибка API (код {status or '—'}): {err_detail or 'нет choices в ответе'}",
                "Error",
            )

        content = data["choices"][0]["message"]["content"]

        split_re = rf"(?im)^\s*{_PROMPT_LABEL}\s*:\s*\*{{0,3}}\s*$"
        parts = re.split(split_re, content, maxsplit=1)
        if len(parts) == 1:
            parts = re.split(rf"(?i)\n\s*{_PROMPT_LABEL}\s*:\s*", content, maxsplit=1)
        if len(parts) > 1:
            raw_text = parts[0]
            img_query = parts[1].strip()
        else:
            # Модель забыла поставить «ПРОМПТ:»; пытаемся отрезать хвостовой английский абзац
            raw_text_fallback, trailing_en = _split_trailing_english_prompt(content)
            if trailing_en:
                raw_text = raw_text_fallback
                img_query = trailing_en
            else:
                raw_text = content
                img_query = topic

        text = fix_html_safety(raw_text)
        if p_key == "stern":
            text = _apply_stern_typos(text)
        text = finalize_public_post(
            text, p_key, rubric_plain, is_pension_video, topic_raw=topic_raw
        )

        # Self-critique: один доп. проход. Только если в посте обнаружены явные проблемы.
        # Календарь Ленина и «чтение Ленинианы» не переписываем — там жёстко привязанный
        # шаблон с фактами/цитатами.
        skip_critic = p_key == "lenin" and (
            lenin_event or book_chunk
            or (lenin_content and topic_raw and "[ПСС · фрагмент]" in topic_raw)
        )
        if not skip_critic:
            findings = _selfcritique_findings(p_key, text)
            if p_key == "gdepar":
                findings.extend(_gdepar_body_duplicate_findings(text, recent_bodies))
                # Михалыч: всегда минимум один проход критики при gdepar
                if not findings:
                    findings.append("проверь уникальность: нет ли повтора недавних постов и клише")
            if p_key == "lenin" and lenin_content and not (lenin_event or book_chunk):
                findings.extend(lenin_content.cliche_findings(text, topic_raw))
                if not findings and lenin_content.is_press_polemic_story(text):
                    findings.append(
                        "запрещённый сюжет: полемика/газеты/Невская Звезда — перепиши по другому фрагменту базы"
                    )
            if calendar_seed and p_key == "lenin":
                body_len = len(_post_body_without_hashtags(text))
                if body_len < int(calendar_seed.get("min_chars", 1100)):
                    findings.append(
                        f"календарь слишком короткий: {body_len} < {calendar_seed.get('min_chars')}"
                    )
            if rubric_seed and p_key == "lenin" and lenin_content and not calendar_seed:
                body_len = len(_post_body_without_hashtags(text))
                if body_len < int(rubric_seed.get("min_chars", 550)):
                    findings.append(
                        f"рубрика слишком короткая: {body_len} < {rubric_seed.get('min_chars')}"
                    )
            if rubric_seed and p_key == "stern":
                body_len = len(_post_body_without_hashtags(text))
                if body_len < int(rubric_seed.get("min_chars", 550)):
                    findings.append(
                        f"рубрика слишком короткая: {body_len} < {rubric_seed.get('min_chars')}"
                    )
                if not findings and recent_lenin_bodies:
                    findings.append("проверь: другой документ/год/тема, не повтор недавних постов")
            if findings:
                logger.info(f"[selfcritic] {p_key} findings: {findings}")
                rewritten = await _selfcritique_rewrite(p_key, persona, topic, text, findings)
                if rewritten:
                    candidate = fix_html_safety(rewritten)
                    if p_key == "stern":
                        candidate = _apply_stern_typos(candidate)
                    candidate = finalize_public_post(
                        candidate, p_key, rubric_plain, is_pension_video, topic_raw=topic_raw
                    )
                    # Применяем переписку, только если она реально уменьшила число замечаний.
                    new_findings = _selfcritique_findings(p_key, candidate)
                    if len(new_findings) < len(findings):
                        logger.info(
                            f"[selfcritic] {p_key} rewritten: {len(findings)} -> {len(new_findings)} issues"
                        )
                        text = candidate

        if p_key == "lenin":
            if lenin_event:
                match = re.match(r"\d{2}\.\d{2}\.\d{4}\s*[—\-]\s*(.*)", lenin_event)
                if match:
                    img_query = match.group(1).strip()
            elif book_chunk:
                img_query = f"Vladimir Lenin historical archive photography {book_chunk['source']}"

        img_p = f"{persona['style']}. {img_query}"
        if p_key == "gdepar" and gdepar_content:
            gdepar_canon = gdepar_content.resolve_gdepar_image_prompt(topic_raw or topic)
            if gdepar_canon:
                img_p = gdepar_canon
        if p_key == "garden":
            season_bias = {
                3: "early spring, last snow patches, bare soil, indoor seedlings on windowsill, pruning fruit trees",
                4: "mid spring, swelling buds, seedlings in trays, raised beds prepared, first greens",
                5: "late spring in Central Russia, young vegetable seedlings just transplanted into open ground, no ripe fruits, fresh light-green foliage",
                6: "early summer, flowering vegetables, first tiny green fruits, lush garden",
                7: "mid summer, mature plants, first harvest, ripe berries",
                8: "late summer, full harvest, ripe tomatoes and zucchini",
                9: "early autumn, harvest, yellowing leaves, root vegetables",
                10: "mid autumn, bare beds, autumn cleanup, mulching",
                11: "late autumn, frost on the ground, garden cleanup",
                12: "winter, snow-covered garden, dormant trees",
                1: "deep winter, snow, seed planning indoors",
                2: "late winter, indoor seedlings starting under lamps",
            }
            sb = season_bias.get(datetime.now(MSK_TZ).month, "")
            if sb:
                img_p = f"{persona['style']}. {sb}, {img_query}"
        return text, img_p

    except json.JSONDecodeError as e:
        logger.exception("[draft] JSON decode in generate_draft_content")
        return f"Ошибка ИИ (JSON): {e}", "Error"
    except Exception as e:
        logger.exception("[draft] generate_draft_content failed persona=%s topic=%r", p_key, topic_raw)
        return f"Ошибка ИИ: {e}", "Error"

POOL_MIN_SIZE_FOR_RANDOM = 5

# Маппинг темы → подстроки в имени файла. Используется, чтобы при «тяге гири»
# не выпала схема McGill про нагрузку на L5/S1.
# (regex, подстроки в имени файла из пула, branch — для отбора по страницам/качеству).
# В regex даём И русские, И английские термины — это позволяет использовать
# image_prompt (английский) как стабильный topic_hint при регенерации.
_STERN_EXERCISE_MEDIA_CACHE: tuple[float, list[dict]] | None = None


def _load_stern_exercise_media() -> list[dict]:
    global _STERN_EXERCISE_MEDIA_CACHE
    path = "data/stern_exercise_media.json"
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _STERN_EXERCISE_MEDIA_CACHE = (0.0, [])
        return []
    if _STERN_EXERCISE_MEDIA_CACHE and _STERN_EXERCISE_MEDIA_CACHE[0] == mtime:
        return _STERN_EXERCISE_MEDIA_CACHE[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("exercises", [])
    except Exception:
        entries = []
    _STERN_EXERCISE_MEDIA_CACHE = (mtime, entries)
    return entries


def _pick_stern_exercise_image(topic_hint: str, pool_dir: str) -> tuple[str | None, dict]:
    """Точное сопоставление упражнения → картинка из data/stern_exercise_media.json."""
    bl = _pool_blacklist("stern")
    for ex in _load_stern_exercise_media():
        aliases = ex.get("aliases")
        if not aliases:
            continue
        try:
            if not re.search(aliases, topic_hint):
                continue
        except re.error:
            continue
        pool_names = ex.get("pool") or []
        if not pool_names:
            continue
        candidates = []
        for name in pool_names:
            if name in bl:
                continue
            full = os.path.join(pool_dir, name)
            if os.path.isfile(full) and _pool_image_quality_ok(full)[0]:
                candidates.append(full)
        if candidates:
            pick = random.choice(candidates)
            return pick, {
                "pool_state": "exercise_match",
                "exercise_id": ex.get("id"),
                "exercise_name": ex.get("name_ru"),
                "source": ex.get("source"),
                "candidates": len(candidates),
            }
    return None, {"pool_state": "exercise_no_match"}


STERN_TOPIC_RULES: list[tuple[re.Pattern, tuple[str, ...], str]] = [
    (re.compile(
        r"(?i)(гир[яеьюий]|kettlebell|рывок|толчок|мах|swing|snatch|clean|jerk|goblet|"
        r"подъем\s+на\s+грудь|подъём\s+на\s+грудь|getup|turkish)"
    ),
     ("Tsatsouline", "Цацулин", "Поляков", "zanimaites"), "kettle"),
    (re.compile(
        r"(?i)(спин|пояс|осанк|кор[\s,.]|back|posture|abdomin|сутул|корпус|lumbar|spine|"
        r"bird[\s-]?dog|птич[а-я]*[\s\-–]*собак|макгилл|mcgill|grand\s+master|разгибатели|"
        r"erector|paraspinal|тяг[аи][\s,])"
    ),
     ("Back Mechanic", "McGill"), "back"),
    (re.compile(
        r"(?i)(отжимани|подтягиван|планк|воркаут|калистен|собственн[аы]й\s*вес|"
        r"push[\s-]?up|pull[\s-]?up|bodyweight|plank|chin[\s-]?up|dip)"
    ),
     ("Приросший",), "bodyweight"),
    (re.compile(
        r"(?i)(колен|тазобед|сустав|hip|knee|ankle|растяжк|мобильн|разминк|"
        r"гимнастик|разогрев|warm[\s-]?up|подвижн|mobility|stretch|"
        r"joint\s+mobility|rotating\s+shoulders|tilting\s+pelvis)"
    ),
     ("Приросший",), "joint"),
]


_BLACKLIST_CACHE: dict[str, set[str]] = {}


def _pool_blacklist(p_key: str) -> set[str]:
    """Загружает media/<persona>/pool/.blacklist.txt — построчно имена файлов
    (без папки), которые НИКОГДА не выпадают. Кешируется на mtime файла."""
    path = f"media/{p_key}/pool/.blacklist.txt"
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _BLACKLIST_CACHE.pop(p_key, None)
        return set()
    key = f"{p_key}:{mtime}"
    cached = _BLACKLIST_CACHE.get(key)
    if cached is not None:
        return cached
    items: set[str] = set()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    items.add(ln)
    except Exception:
        pass
    _BLACKLIST_CACHE.clear()
    _BLACKLIST_CACHE[key] = items
    return items

_STERN_PAGE_RE = re.compile(r"_p(\d{4})_", re.IGNORECASE)


def _stern_pool_page_num(path: str) -> int | None:
    m = _STERN_PAGE_RE.search(os.path.basename(path))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _pool_image_quality_ok(path: str) -> tuple[bool, dict]:
    """Отсекаем обложки-«плакаты», чутьё черные сканы и однотонные куски."""
    try:
        from PIL import Image, ImageStat

        with Image.open(path) as im:
            im = im.convert("RGB")
            if max(im.size) > 400:
                im.thumbnail((400, 400))
            st = ImageStat.Stat(im)
        means = st.mean
        stds = st.stddev
        avg_m = sum(means) / 3.0
        avg_s = sum(stds) / 3.0
        meta = {"mean": round(avg_m, 1), "std": round(avg_s, 1)}
        if avg_m < 42 or avg_m > 245:
            return False, {**meta, "reject": "brightness"}
        if avg_s < 14:
            return False, {**meta, "reject": "flat_or_noise"}
        return True, meta
    except Exception as e:
        return False, {"reject": "read_error", "err": str(e)[:80]}


def _filter_stern_pool_paths(paths: list[str], branch: str) -> list[str]:
    bl = _pool_blacklist("stern")
    out: list[str] = []
    for p in paths:
        if os.path.basename(p) in bl:
            continue
        pg = _stern_pool_page_num(p)
        # Поднимаем порог для kettle: страницы 1–12 у Цацулина/Полякова —
        # обложки, форзацы, гербы RKC, оглавления, предисловия.
        if branch == "kettle" and pg is not None and pg <= 12:
            continue
        if branch == "back" and pg is not None and pg <= 4:
            continue
        if branch == "joint" and pg is not None and pg <= 10:
            continue
        if branch == "bodyweight" and pg is not None and pg <= 6:
            continue
        ok, _q = _pool_image_quality_ok(p)
        if ok:
            out.append(p)
    return out

# Негативный промпт для fal/flux/dev по персонам — то, чего НЕ должно быть на картинке.
PERSONA_NEGATIVE_PROMPTS = {
    "gdepar": (
        "household sweeping broom, straw broom, witch broom, kitchen broom, dust broom, "
        "twig broom for floor, plastic broom, pine needles, fir branch, spruce, conifer, "
        "single decorative branch, christmas tree greenery, modern bathroom, shower, jacuzzi, "
        "spa hotel, gym, vehicle, automobile, truck, exterior shot of building, snow, "
        "people in modern clothing, neon lights, English text, watermark"
    ),
    "stern": (
        "anime, cartoon, plastic figure, mascot, child, female model, fashion shoot, "
        "logo, watermark, distorted limbs, extra fingers, English text overlay"
    ),
    "garden": (
        "winter scenery, snow, frost, ripe red fruits in May, dead leaves, "
        "watermark, logo, text overlay"
    ),
}


def _pick_pool_image(p_key: str, topic_hint: str | None) -> tuple[str | None, dict]:
    """Возвращает (path, debug_info) с учётом темы поста. None — если пул мал
    или не нашлось ничего по теме (для маленьких пулов мы лучше пойдём в fal)."""
    pool_dir = f"media/{p_key}/pool"
    if not os.path.isdir(pool_dir):
        return None, {"pool_state": "absent"}
    try:
        # Порог 8 кБ: иллюстрации в книжных PDF (Цацулин/МакГилл) — часто
        # компактные ч/б рисунки 8–25 кБ, их нельзя отсекать как «мусор».
        # Реальные обрезки/иконки обычно сильно меньше.
        files = [
            os.path.join(pool_dir, f) for f in os.listdir(pool_dir)
            if not f.startswith(".")
            and f.lower().endswith((".jpg", ".jpeg", ".png"))
            and os.path.getsize(os.path.join(pool_dir, f)) > 8_000
        ]
    except Exception:
        return None, {"pool_state": "error"}

    bl = _pool_blacklist(p_key)
    bl_used_count = 0
    if bl:
        prev = len(files)
        files = [p for p in files if os.path.basename(p) not in bl]
        bl_used_count = prev - len(files)

    if not files:
        return None, {"pool_state": "empty", "blacklist_skipped": bl_used_count}

    def quality_only(paths: list[str]) -> list[str]:
        return [p for p in paths if _pool_image_quality_ok(p)[0]]

    if p_key == "stern" and topic_hint:
        ex_pick, ex_dbg = _pick_stern_exercise_image(topic_hint, pool_dir)
        if ex_pick:
            return ex_pick, ex_dbg
        for pat, authors, branch in STERN_TOPIC_RULES:
            if pat.search(topic_hint):
                matched = [
                    p for p in files
                    if any(a.lower() in os.path.basename(p).lower() for a in authors)
                ]
                filtered = _filter_stern_pool_paths(matched, branch)
                if filtered:
                    pick = random.choice(filtered)
                    return pick, {
                        "pool_state": "topic_match",
                        "pool_count": len(files),
                        "matched_count": len(matched),
                        "filtered_count": len(filtered),
                        "branch": branch,
                        "authors": list(authors),
                    }
                return None, {
                    "pool_state": "topic_filtered_empty",
                    "pool_count": len(files),
                    "matched_count": len(matched),
                    "branch": branch,
                    "authors": list(authors),
                }

    if len(files) < POOL_MIN_SIZE_FOR_RANDOM:
        return None, {"pool_state": "too_small", "pool_count": len(files)}

    if p_key in ("stern", "gdepar"):
        ok_files = quality_only(files)
        if not ok_files:
            return None, {"pool_state": "quality_empty", "pool_count": len(files)}
        pick = random.choice(ok_files)
        return pick, {"pool_state": "random", "pool_count": len(files), "quality_ok": len(ok_files)}

    pick = random.choice(files)
    return pick, {"pool_state": "random", "pool_count": len(files)}


def _image_hints_for_venik(topic_raw: str | None, image_prompt: str | None) -> str:
    """Только тема слота — LLM-промпт с «whisk» не должен включать канон веника."""
    return (topic_raw or "").strip()[:600]


def _save_image_bytes_as_jpeg(raw: bytes, dest_path: str) -> None:
    """PNG/WebP от Gemini → JPEG для черновиков Telegram."""
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(dest_path, "JPEG", quality=92)
    except Exception:
        with open(dest_path, "wb") as f:
            f.write(raw)


async def _generate_gemini_venik_image(prompt: str, dest_path: str) -> bool:
    """Nano Banana (Gemini flash image) — только для веников Gdepar."""
    if not GEMINI_API_KEY or not gdepar_content:
        return False
    cfg = getattr(gdepar_content, "GDEPAR_VENIK_GEMINI", {}) or {}
    model = (
        os.getenv("GDEPAR_VENIK_GEMINI_MODEL")
        or cfg.get("model")
        or "gemini-2.5-flash-image"
    ).strip()
    aspect = (os.getenv("GDEPAR_VENIK_GEMINI_ASPECT") or cfg.get("aspect_ratio") or "4:3").strip()
    image_size = (os.getenv("GDEPAR_VENIK_GEMINI_SIZE") or cfg.get("image_size") or "1K").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "responseFormat": {
                "image": {"aspectRatio": aspect, "imageSize": image_size},
            },
        },
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                url,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if res.status_code != 200:
                # Старые модели без responseFormat — упрощённый запрос
                payload_simple = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE"]},
                }
                res = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload_simple,
                )
            if res.status_code != 200:
                err_body = (res.text or "")[:400]
                logger.warning(
                    "[gdepar] gemini venik HTTP %s: %s",
                    res.status_code,
                    err_body,
                )
                if res.status_code == 429:
                    logger.warning(
                        "[gdepar] gemini quota exceeded — включите billing в AI Studio "
                        "или GDEPAR_VENIK_FLUX_FALLBACK=1 для запасного Flux"
                    )
                return False
            data = res.json()
            for cand in data.get("candidates") or []:
                for part in (cand.get("content") or {}).get("parts") or []:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if not inline:
                        continue
                    b64 = inline.get("data")
                    if not b64:
                        continue
                    _save_image_bytes_as_jpeg(base64.b64decode(b64), dest_path)
                    logger.info("[gdepar] venik via gemini model=%s", model)
                    return True
    except Exception as e:
        logger.warning("[gdepar] gemini venik error: %s", e)
    return False


async def generate_image(
    prompt,
    d_id,
    p_key,
    topic_hint: str | None = None,
    topic_raw: str | None = None,
):
    if p_key == "pension":
        return None
    if (
        p_key == "gdepar"
        and gdepar_content
        and gdepar_content.CLASSIC_RUBRIC_TAG in (topic_raw or "")
    ):
        logger.info("[gdepar] classic_banya: skip flux — только портрет автора")
        return None
    if p_key == "lenin":
        return await _lenin_wikipedia_image(
            prompt=prompt,
            d_id=d_id,
            topic_raw=topic_raw,
            topic_hint=topic_hint,
        )

    venik_blob = _image_hints_for_venik(topic_raw, topic_hint or prompt)
    venik_canon = None
    gdepar_canon = None
    venik_provider = None
    if p_key == "gdepar" and gdepar_content:
        venik_provider = gdepar_content.venik_image_provider()
        gdepar_canon = gdepar_content.resolve_gdepar_image_prompt(
            venik_blob, provider=venik_provider
        )
        venik_canon = gdepar_content.resolve_venik_image_prompt(
            venik_blob, provider=venik_provider
        )
        if gdepar_canon:
            prompt = gdepar_canon

    if venik_canon or gdepar_canon:
        src, pool_dbg = None, {"pool_state": "gdepar_canonical_skip_pool"}
    else:
        src, pool_dbg = _pick_pool_image(p_key, topic_hint or topic_raw)
    if src:
        dst = f"media/draft_{d_id}.jpg"
        try:
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
            logger.info(f"[{p_key}] using pool image: {os.path.basename(src)} ({pool_dbg.get('pool_state')})")
            return dst
        except Exception as e:
            logger.warning(f"[{p_key}] pool copy error: {e}")

    path = f"media/draft_{d_id}.jpg"
    if venik_canon and venik_provider == "gemini":
        if await _generate_gemini_venik_image(prompt, path):
            return path
        flux_fb = os.getenv("GDEPAR_VENIK_FLUX_FALLBACK", "").strip().lower() in (
            "1", "true", "yes", "on",
        )
        if not flux_fb:
            logger.warning(
                "[gdepar] gemini venik failed; flux fallback OFF "
                "(GDEPAR_VENIK_FLUX_FALLBACK=1 чтобы включить)"
            )
            return None
        logger.warning("[gdepar] gemini venik failed — fallback to flux")
        flux_prompt = gdepar_content.resolve_venik_image_prompt(venik_blob, provider="flux")
        if flux_prompt:
            prompt = flux_prompt

    if not FAL_KEY:
        return None
    neg = PERSONA_NEGATIVE_PROMPTS.get(p_key, "")
    venik_flux = {}
    if venik_canon and gdepar_content:
        venik_flux = getattr(gdepar_content, "GDEPAR_VENIK_FLUX", {}) or {}
        extra = getattr(gdepar_content, "GDEPAR_VENIK_NEGATIVE_EXTRA", "")
        neg = f"{neg}, {extra}" if neg and extra else (extra or neg)
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            flux_steps = venik_flux.get("num_inference_steps", 32 if gdepar_canon else 28)
            flux_guidance = venik_flux.get("guidance_scale", 4.5 if gdepar_canon else 3.5)
            flux_size = venik_flux.get("image_size", "square_hd")
            payload = {
                "prompt": prompt,
                "image_size": flux_size if venik_canon else "square_hd",
                "num_inference_steps": flux_steps,
                "guidance_scale": flux_guidance,
            }
            if neg:
                payload["negative_prompt"] = neg
            res = await client.post(
                "https://fal.run/fal-ai/flux/dev",
                headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            if res.status_code != 200 and not (venik_canon or gdepar_canon):
                # schnell без negative — только не для канонических веников
                payload_schnell = {"prompt": prompt, "image_size": "square_hd", "num_inference_steps": 4}
                res = await client.post(
                    "https://fal.run/fal-ai/flux/schnell",
                    headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
                    json=payload_schnell,
                )
            if res.status_code == 200:
                img_url = res.json().get("images", [{}])[0].get("url")
                if img_url:
                    img_res = await client.get(img_url)
                    with open(path, "wb") as f:
                        f.write(img_res.content)
                    return path
    except Exception as e:
        logger.warning(f"[{p_key}] fal error: {e}")
    return None

DRAFT_PREVIEW_DIR = "/root/projects/empire/static/drafts"
DRAFT_PREVIEW_BASE_URL = os.environ.get("DRAFT_PREVIEW_BASE_URL", "https://neverretire.ru/static/drafts")


def _publish_draft_preview(d_id: int, src: str) -> str | None:
    """Кладёт картинку черновика в публичную static-папку и возвращает её URL
    для использования в Telegram link-preview. Возвращает None при ошибке."""
    try:
        os.makedirs(DRAFT_PREVIEW_DIR, exist_ok=True)
        dst = os.path.join(DRAFT_PREVIEW_DIR, f"d_{d_id}.jpg")
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        cache_buster = int(datetime.now().timestamp())
        return f"{DRAFT_PREVIEW_BASE_URL}/d_{d_id}.jpg?v={cache_buster}"
    except Exception as e:
        logger.warning(f"[notify] preview publish failed: {e}")
        return None


_CAPTION_CONT_FOOTER = "\n\n<i>↓ продолжение ниже</i>"
_CAPTION_CONT_HEADER = "<i>↑ продолжение (часть 1 — с фото)</i>\n\n"


def _admin_caption_for_photo(text: str, *, max_len: int = 1024) -> tuple[str, str | None]:
    """
    Caption для send_photo. Если текст длиннее лимита Telegram — возвращает
    (часть_1 + указатель вниз, только_продолжение_с_указателем_вверх).
    Второе сообщение не дублирует первое.
    """
    if len(text) <= max_len:
        return text, None
    reserve = len(_CAPTION_CONT_FOOTER)
    budget = max(120, max_len - reserve)
    chunk = text[:budget]
    split_at = chunk.rfind("\n\n")
    if split_at < int(budget * 0.45):
        for sep in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
            pos = chunk.rfind(sep)
            if pos >= int(budget * 0.35):
                split_at = pos + len(sep)
                break
    if split_at < 80:
        split_at = budget
    part1 = text[:split_at].rstrip()
    part2 = text[split_at:].lstrip()
    if not part2:
        part1 = text[: max_len - reserve].rstrip()
        part2 = text[len(part1) :].lstrip()
    caption = f"{part1}{_CAPTION_CONT_FOOTER}"
    if len(caption) > max_len:
        caption = f"{text[: max_len - reserve].rstrip()}{_CAPTION_CONT_FOOTER}"
        part2 = text[len(caption) - len(_CAPTION_CONT_FOOTER) :].lstrip()
    continuation = f"{_CAPTION_CONT_HEADER}{part2}" if part2 else None
    return caption, continuation


def _curated_rubric_requires_photo(p_key: str, topic_raw: str | None) -> bool:
    topic = topic_raw or ""
    if p_key == "gdepar" and gdepar_content and gdepar_content.CLASSIC_RUBRIC_TAG in topic:
        return True
    if p_key == "gdepar" and "[Дуэт]" in topic:
        return True
    if p_key == "lenin" and "[#Вэтотдень]" in topic:
        return True
    if p_key == "lenin" and lenin_content and lenin_content.requires_curated_photo(topic):
        return True
    if p_key == "stern" and stern_content and stern_content.is_curated_topic(topic):
        return True
    if p_key == "stern" and any(
        tag in topic
        for tag in (
            "[Рутина]",
            "[Психология]",
            "[Восстановление]",
            "[Питание]",
            "[Срывы]",
            "[Мотивация]",
            "[Возрастной тренинг]",
            "[Ответы]",
        )
    ):
        return True
    return False


def _curated_has_photo(img_f: str | None) -> bool:
    return bool(img_f and os.path.exists(img_f))


def _record_stern_technique_if_published(draft: PostDraft) -> None:
    if draft.persona_key != "stern" or "[Техника гирь]" not in (draft.topic_raw or ""):
        return
    try:
        import stern_technique as st

        eid = st.entry_id_from_topic(draft.topic_raw)
        if eid:
            st.record_published(eid)
    except Exception as exc:
        logger.warning("[stern_technique] record_published: %s", exc)


def _record_stern_comic_if_published(draft: PostDraft) -> None:
    if draft.persona_key != "stern" or "[Комик техника]" not in (draft.topic_raw or ""):
        return
    try:
        import stern_comic_video as scv

        eid = scv.entry_id_from_topic(draft.topic_raw)
        if eid:
            scv.record_published(eid)
    except Exception as exc:
        logger.warning("[stern_comic_video] record_published: %s", exc)


def _curated_body_too_short(text: str | None) -> bool:
    from rubric_posts import MIN_CURATED_BODY_CHARS

    plain = re.sub(r"<[^>]+>", "", text or "")
    return len(plain.strip()) < MIN_CURATED_BODY_CHARS


async def notify_admin(d_id, p_key, text, img_f, *, topic_raw: str | None = None):
    curated_photo = _curated_rubric_requires_photo(p_key, topic_raw)
    has_photo = _curated_has_photo(img_f)
    short_body = curated_photo and _curated_body_too_short(text)
    buttons: list = []
    if not curated_photo or has_photo:
        buttons.append(
            [InlineKeyboardButton(text="🚀 Опубликовать", callback_data=f"send_{d_id}")]
        )
    buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{d_id}")])
    if curated_photo:
        buttons.insert(
            1,
            [
                InlineKeyboardButton(
                    text="🖼 Другая картинка",
                    callback_data=f"curimg_{d_id}",
                )
            ],
        )
    elif p_key not in ["pension", "lenin"]:
        buttons.insert(1, [
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"regen_{d_id}"),
            InlineKeyboardButton(text="🚫 В корзину", callback_data=f"badimg_{d_id}"),
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    # Stern: всегда фото + caption (не разносить превью и текст без картинки).
    force_photo_caption = p_key == "stern"

    if img_f and os.path.exists(img_f) and _is_video_path(img_f):
        cap_limit = 1024 if force_photo_caption else 1000
        caption, continuation = _admin_caption_for_photo(text, max_len=cap_limit)
        if short_body:
            from rubric_posts import MIN_CURATED_BODY_CHARS

            warn = (
                f"⚠️ Короткий пост (<{MIN_CURATED_BODY_CHARS} симв.) — проверьте цитату.\n\n"
            )
            caption = warn + caption
        await bot.send_video(
            ADMIN_ID, video=FSInputFile(img_f), caption=caption, reply_markup=kb, parse_mode="HTML"
        )
        if continuation:
            await bot.send_message(ADMIN_ID, continuation, parse_mode="HTML")
    elif img_f and os.path.exists(img_f):
        cap_limit = 1024 if force_photo_caption else 1000
        caption, continuation = _admin_caption_for_photo(text, max_len=cap_limit)
        if short_body:
            from rubric_posts import MIN_CURATED_BODY_CHARS

            warn = (
                f"⚠️ Короткий пост (<{MIN_CURATED_BODY_CHARS} симв.) — проверьте цитату.\n\n"
            )
            caption = warn + caption
        await bot.send_photo(
            ADMIN_ID, photo=FSInputFile(img_f), caption=caption, reply_markup=kb, parse_mode="HTML"
        )
        if continuation:
            await bot.send_message(ADMIN_ID, continuation, parse_mode="HTML")
    else:
        if curated_photo:
            status_text = (
                "⚠️ <b>Рубрика без фото</b> — в канал нельзя. "
                "На сервере: <code>./scripts/activate_curated_rubrics.sh</code> "
                "(prefetch gdepar/lenin/stern). Кнопка «Опубликовать» скрыта.\n\n"
            )
        else:
            status_text = "🖼 [БЕЗ ФОТО]\n\n" if p_key != "pension" else "📰 [СВОДКА]\n\n"
        if short_body:
            from rubric_posts import MIN_CURATED_BODY_CHARS

            status_text = (
                "⚠️ <b>Короткий пост</b> — для рубрики нужна полная цитата и источник "
                f"(≥{MIN_CURATED_BODY_CHARS} симв.). Дополните запись в JSON или отклоните.\n\n"
            ) + status_text
        await bot.send_message(ADMIN_ID, f"{status_text}{text}", reply_markup=kb, parse_mode="HTML")


@dp.message(Command("obsidian"))
async def cmd_obsidian(message: types.Message):
    """Вариант A: импорт, список очереди, принудительный черновик."""
    if message.from_user.id != ADMIN_ID:
        return
    import obsidian_content as oc

    parts = (message.text or "").split()
    sub = parts[1].lower() if len(parts) > 1 else "help"

    if sub == "import":
        ok = oc.run_import_if_needed(force=True)
        n = len(oc.load_queue())
        await message.answer(f"Импорт: {'OK' if ok else 'пропуск/ошибка'}. В очереди: {n} заметок.")
        return

    if sub in ("list", "queue"):
        rows = oc.load_queue()
        if not rows:
            await message.answer("Очередь пуста. Задайте OBSIDIAN_EMPIRE_INCOMING и /obsidian import")
            return
        lines = []
        for r in rows[:15]:
            lines.append(
                f"• <b>{html_std.escape(str(r.get('title', '')))}</b> "
                f"({r.get('persona')}) {r.get('scheduled') or 'без времени'} "
                f"[{r.get('status')}] id=<code>{html_std.escape(str(r.get('id', '')))}</code>"
            )
        tail = f"\n…ещё {len(rows) - 15}" if len(rows) > 15 else ""
        await message.answer("Obsidian queue:\n" + "\n".join(lines) + tail, parse_mode="HTML")
        return

    if sub == "due":
        due = oc.entries_due()
        if not due:
            await message.answer("Нет просроченных/готовых по времени постов.")
            return
        for entry in due:
            d_id = await _dispatch_obsidian_entry(entry)
            await message.answer(f"Черновик #{d_id} из Obsidian: {entry.get('title')}")
        return

    if sub == "now" and len(parts) > 2:
        target = parts[2].strip()
        for r in oc.load_queue():
            if r.get("id") == target:
                d_id = await _dispatch_obsidian_entry(r)
                await message.answer(f"Черновик #{d_id}: {r.get('title')}")
                return
        await message.answer(f"Нет id={target} в obsidian_import_queue.json")
        return

    if sub == "image" and len(parts) > 2:
        try:
            d_id = int(parts[2].strip())
        except ValueError:
            return await message.answer("Использование: /obsidian image &lt;draft_id&gt;", parse_mode="HTML")
        async with async_session() as session:
            draft = await session.get(PostDraft, d_id)
            if not draft:
                return await message.answer(f"Нет черновика #{d_id}")
            img_f = await oc.resolve_image_for_topic_raw(
                draft.topic_raw, generate_image, d_id, draft.persona_key
            )
            if not img_f:
                eid = oc.parse_obsidian_entry_id(draft.topic_raw)
                entry = oc.queue_entry_by_id(eid) if eid else None
                want = (entry or {}).get("image") or "?"
                return await message.answer(
                    f"Файл не найден на VPS.\nОжидается: {want}\n"
                    "Скопируйте в Empire/pension/queue/attachments/ на ПК → sync Диска."
                )
            draft.image_path = img_f
            await session.commit()
        await notify_admin(d_id, draft.persona_key, draft.text_content, img_f, topic_raw=draft.topic_raw)
        return await message.answer(f"Картинка прикреплена к #{d_id}")

    await message.answer(
        "<b>Obsidian (вариант A)</b>\n"
        "/obsidian import — переимпорт .md\n"
        "/obsidian list — очередь JSON\n"
        "/obsidian due — все с наступившим scheduled → черновики\n"
        "/obsidian now &lt;id&gt; — один пост сейчас\n"
        "/obsidian image &lt;draft_id&gt; — подтянуть картинку из vault",
        parse_mode="HTML",
    )


@dp.message(Command("draft"))
async def cmd_manual(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return await message.answer("Формат: /draft [персона] [тема]")
    
    p_key, topic = args[1], args[2]
    wait = await message.answer(f"⏳ Работаю над черновиком...")
    text, img_p = await generate_draft_content(p_key, topic)
    
    async with async_session() as session:
        draft = PostDraft(persona_key=p_key, text_content=text, image_prompt=img_p, topic_raw=topic, decision="pending")
        session.add(draft); await session.commit()
        d_id = draft.id

    img_f = await generate_image(img_p, d_id, p_key, topic_hint=img_p, topic_raw=topic)
    async with async_session() as session:
        d = await session.get(PostDraft, d_id)
        d.image_path = img_f
        if img_p and p_key == "gdepar" and gdepar_content:
            canon = gdepar_content.resolve_gdepar_image_prompt(topic)
            if canon:
                d.image_prompt = canon
        await session.commit()

    await _record_topic_history(p_key, topic, d_id)

    await wait.delete()
    await notify_admin(d_id, p_key, text, img_f)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Сводка решений модератора и регенов за последние 7/30 дней."""
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=1)
    days = 7
    if len(args) > 1:
        try:
            days = max(1, min(365, int(args[1])))
        except Exception:
            pass
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session() as session:
        res = await session.execute(
            select(PostDraft).where(PostDraft.created_at >= since)
        )
        drafts = res.scalars().all()

    by_persona: dict[str, dict] = {}
    for d in drafts:
        b = by_persona.setdefault(d.persona_key or "?", {
            "total": 0, "approved": 0, "auto": 0, "rejected": 0, "pending": 0,
            "regen": 0, "badimg": 0,
        })
        b["total"] += 1
        dec = d.decision or "pending"
        if dec == "approved":
            b["approved"] += 1
        elif dec == "auto":
            b["auto"] += 1
        elif dec == "rejected":
            b["rejected"] += 1
        else:
            b["pending"] += 1
        b["regen"] += int(d.regen_count or 0)
        b["badimg"] += int(d.bad_image_count or 0)

    if not by_persona:
        return await message.answer(f"📊 За {days} дн. черновиков нет.")

    lines = [f"📊 <b>Стата за {days} дн.</b>"]
    order = ["pension", "stern", "gdepar", "garden", "lenin"]
    seen = set()
    for key in order + sorted(by_persona.keys()):
        if key in seen or key not in by_persona:
            continue
        seen.add(key)
        b = by_persona[key]
        total = b["total"] or 1
        appr_all = b["approved"] + b["auto"]
        appr_pct = round(100 * appr_all / total)
        rej_pct = round(100 * b["rejected"] / total)
        lines.append(
            f"<b>{key}</b>: {b['total']} шт. ✅{appr_all} ({appr_pct}%, авто {b['auto']}) "
            f"❌{b['rejected']} ({rej_pct}%) ⏳{b['pending']} "
            f"| 🔄{b['regen']} 🚫{b['badimg']}"
        )

    # Топ-3 удалённых тем — что не зашло.
    rejected_topics = [
        d.topic_raw for d in drafts if d.decision == "rejected" and d.topic_raw
    ]
    if rejected_topics:
        top_rej = rejected_topics[:5]
        lines.append("\n<b>Отклонённые темы (последние):</b>")
        for t in top_rej:
            lines.append(f"• {t[:80]}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    """Последние темы по персоне: /history <persona> [days]"""
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Формат: /history <persona> [days]")
    p_key = args[1]
    days = 30
    if len(args) > 2:
        try:
            days = max(1, min(365, int(args[2])))
        except Exception:
            pass
    recent = await _recent_topics(p_key, days=days, limit=30)
    if not recent:
        return await message.answer(f"История {p_key} за {days} дн. пуста.")
    lines = [f"<b>История {p_key} за {days} дн.</b> ({len(recent)} шт.):"]
    for r in recent[:25]:
        lines.append(f"• {r['created_at'].strftime('%m-%d')} — {r['topic_raw'][:80]}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("spy"))
async def cmd_spy(message: types.Message):
    """Разведка: список сигналов и пакетное создание черновиков."""
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    async with async_session() as session:
        if len(args) >= 2 and args[1] == "draft":
            limit = 2
            if len(args) >= 3:
                try:
                    limit = max(1, min(5, int(args[2])))
                except Exception:
                    pass
            from spy_to_draft import batch_drafts_from_spy

            wait = await message.answer(f"⏳ Черновики из spy (до {limit})…")
            stats = await batch_drafts_from_spy(session, limit=limit)
            await wait.edit_text(
                f"✅ spy→draft: создано {stats.get('created', 0)}, "
                f"ошибок {stats.get('errors', 0)}\n"
                f"ids: {stats.get('draft_ids', [])}"
            )
            for d_id in stats.get("draft_ids", []):
                d = await session.get(PostDraft, d_id)
                if d:
                    await notify_admin(d_id, d.persona_key, d.text_content, d.image_path)
            return
        if len(args) >= 3 and args[1] == "one":
            try:
                sid = int(args[2])
            except Exception:
                return await message.answer("Формат: /spy one <id>")
            from spy_to_draft import create_draft_from_spy

            wait = await message.answer(f"⏳ Черновик из spy #{sid}…")
            res = await create_draft_from_spy(session, sid)
            if not res.get("ok"):
                return await wait.edit_text(f"❌ {res.get('error', 'fail')}")
            d_id = res["draft_id"]
            d = await session.get(PostDraft, d_id)
            await wait.delete()
            if d:
                await notify_admin(d_id, d.persona_key, d.text_content, d.image_path)
            return
        rows = (
            await session.execute(
                select(SpySignal)
                .where(SpySignal.status == "new")
                .order_by(desc(SpySignal.anomaly_score))
                .limit(8)
            )
        ).scalars().all()
    if not rows:
        return await message.answer("🕵️ Новых spy_signals нет.")
    lines = ["🕵️ <b>Spy (new)</b>", "/spy draft [N] — пакет черновиков", "/spy one <id> — один"]
    for s in rows:
        prev = (s.post_text or "")[:60].replace("<", "")
        lines.append(f"#{s.id} [{s.persona_key}] ER={s.er_proxy} — {prev}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("scout"))
async def cmd_scout(message: types.Message):
    """Прогнать скаут вручную и показать свежий улов: /scout [persona]"""
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    want_persona = args[1] if len(args) > 1 else None
    await message.answer("⏳ Бегу собирать заголовки...")
    await _refresh_scout_if_stale(max_age_sec=0)  # форс
    try:
        with open(_SCOUT_TRENDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return await message.answer(f"Не удалось прочитать current_trends.json: {e}")

    lines = [f"📰 <b>Скаут</b> ({data.get('updated_at', '?')})"]
    if not want_persona or want_persona == "pension":
        f_news = data.get("financial_news", []) or []
        p_news = data.get("politics_news", []) or []
        lines.append(f"\n<b>pension</b>: финансы={len(f_news)}, политика={len(p_news)}")
        for n in (f_news + p_news)[:6]:
            lines.append(f"  {n}")

    topics = (data.get("topics") or {})
    for p in ("gdepar", "garden", "lenin"):
        if want_persona and want_persona != p:
            continue
        items = topics.get(p, []) or []
        lines.append(f"\n<b>{p}</b>: {len(items)} заголовка")
        for n in items[:8]:
            lines.append(f"  {n}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("diag"))
async def cmd_diag(message: types.Message):
    """Самодиагностика Empire: таймеры, аудит, бэкапы, автопочинка."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🩺 Запускаю самодиагностику…")
    env = os.environ.copy()
    env["EMPIRE_DIAG_NO_TELEGRAM"] = "1"
    env["EMPIRE_DIAG_PRINT_REPORT"] = "1"
    proc = await asyncio.create_subprocess_exec(
        str(EMPIRE_ROOT / "venv/bin/python"),
        str(EMPIRE_ROOT / "scripts/empire_diagnostics_watchdog.py"),
        cwd=str(EMPIRE_ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        await message.answer(
            "⏱ Таймаут 3 мин — смотри /var/log/empire/diagnostics-watchdog.log"
        )
        return
    text = (stdout.decode("utf-8", errors="replace") if stdout else "").strip()
    if not text:
        latest = Path("/var/log/empire/diagnostics-watchdog.log")
        if latest.is_file():
            text = latest.read_text(encoding="utf-8", errors="replace")[-3500:]
        else:
            text = "Отчёт пуст — watchdog ещё не запускался."
    max_len = 3900
    if len(text) > max_len:
        text = "…\n" + text[-max_len:]
    await message.answer(text)


@dp.message(Command("autopublish"))
async def cmd_autopublish(message: types.Message):
    """Показать настройки авто-публикации из data/auto_publish.json"""
    if message.from_user.id != ADMIN_ID:
        return
    cfg = _load_auto_publish_config()
    defs = cfg.get("defaults") or {}
    lines = [
        "⚙️ <b>Авто-публикация</b> <code>data/auto_publish.json</code>",
        f"Глобально: <b>{'ON' if cfg.get('enabled') else 'OFF'}</b>",
        f"Только расписание: {cfg.get('scheduled_only', True)}",
        f"Уведомление админу (короткое): {cfg.get('notify_admin_compact', True)}",
        "",
        "<b>defaults:</b>",
        f"  min_body_chars={defs.get('min_body_chars')}, require_image={defs.get('require_image')}, "
        f"require_zero_regen={defs.get('require_zero_regen')}, require_zero_badimg={defs.get('require_zero_badimg')}, "
        f"max_selfcrit_issues={defs.get('max_selfcrit_issues')}",
        "",
        "<b>personas:</b>",
    ]
    for pk, per in sorted((cfg.get("personas") or {}).items()):
        if str(pk).startswith("_"):
            continue
        lines.append(f"  <code>{pk}</code>: enabled={per.get('enabled')} min_chars={per.get('min_body_chars', '—')}")
    lines.append("")
    lines.append("Чтобы включить: <code>enabled: true</code> и для персоны <code>enabled: true</code>.")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ─────────────────────────────────────────────────────────────
#  Управление картой бань gdepar.ru
# ─────────────────────────────────────────────────────────────

def _banya_status_icon(status: str | None) -> str:
    return {"published": "🟢", "draft": "🟡", "hidden": "⚪"}.get(status or "draft", "🟡")


async def _find_banya(session, ref: str) -> BanyaSpot | None:
    """ref — это либо id числом, либо slug."""
    try:
        if ref.isdigit():
            return await session.get(BanyaSpot, int(ref))
    except Exception:
        pass
    res = await session.execute(select(BanyaSpot).where(BanyaSpot.slug == ref))
    return res.scalar_one_or_none()


@dp.message(Command("banya"))
async def cmd_banya(message: types.Message):
    """Управление списком бань. Подкоманды:
      /banya list [city]                       — список (опционально по городу)
      /banya draft [region] [page]             — черновики (region: MO|SPB|MSK; page≥1)
      /banya info <id|slug>                    — карточка
      /banya pub <id|slug>                     — опубликовать на сайте
      /banya hide <id|slug>                    — скрыть
      /banya visited <id|slug> on|off          — отметка «ходили лично»
      /banya clip <id|slug> <url> [подпись]    — добавить ролик (VK/Rutube/YT/TG/mp4)
      /banya clips <id|slug>                   — показать ролики бани
      /banya clipdel <id|slug> <index>         — удалить ролик по номеру из /banya clips
      /banya seed                              — залить из data/gdepar_spots_seed.json
      /banya osm [regions]                     — обновить из OSM (по умолчанию MO,SPB)
      /banya enrich <id|region> [limit]        — Яндекс: телефон, рейтинг, URL
      /banya reviews <id> [max]                — собрать отзывы с Яндекса (status='pending')
      /banya pending [page]                    — отзывы на модерацию
      /banya approve <review_id>               — публикуем отзыв
      /banya rhide <review_id>                 — отклоняем отзыв
      /banya approvebulk [--apply] [--min-rating N] [--min-text N] [--limit N] [--source SRC] [--require-rating]
                                                — массово pending→approved (без --apply — только отчёт)
      /banya moderateai [аргументы как у скрипта]   — ИИ+RAG модерация (см. tools/banya_review_moderate_ai.py)
      /banya daily                             — ночной yandex_scrape daily; после отзывов — ИИ-модерация при OPENROUTER_API_KEY (off: BANYA_DAILY_MODERATE_AI=0)
      /banya report                            — утренний отчёт сейчас (как cron 07:00)
      /banya dups                              — показать ложные дубли yandex_url
      /banya dedupe                            — очистить ложные привязки у дублей
      /banya refresh <region|id> [limit] [needreviews]
                                                — освежить rating/reviews/site; needreviews —
                                                  только где reviews_total пусто/0
      /banya pubauto [--dry|--apply] [region] [min_rating] [min_reviews] [limit]
                                                — массовая публикация по фильтру
                                                  (пример: /banya pubauto --dry MO 4.0 0)
      /banya hidenoise [--apply] [region]      — скрыть generic-драфты без яндекса/рейтинга
    """
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.answer(cmd_banya.__doc__, parse_mode=None)
    sub = args[1].lower()

    if sub == "list":
        city = args[2] if len(args) > 2 else None
        async with async_session() as session:
            stmt = select(BanyaSpot).order_by(BanyaSpot.city, BanyaSpot.title)
            if city:
                stmt = stmt.where(BanyaSpot.city == city)
            res = await session.execute(stmt)
            spots = list(res.scalars().all())
        if not spots:
            return await message.answer("Пусто. Добавьте: /banya seed или /banya add ...")
        lines = [f"<b>Бани</b> ({len(spots)}):"]
        for s in spots:
            lines.append(
                f"{_banya_status_icon(s.status)} <code>#{s.id}</code> "
                f"<b>{html_std.escape(s.title or '?')}</b> · {html_std.escape(s.city or '?')}"
            )
        return await message.answer("\n".join(lines), parse_mode="HTML")

    if sub == "seed":
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "tools/seed_banya_spots.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
            return await message.answer(
                f"<pre>{html_std.escape((out or err).decode('utf-8', errors='replace')[:1500])}</pre>",
                parse_mode="HTML",
            )
        except Exception as e:
            return await message.answer(f"Сидинг упал: {e}")

    if sub == "osm":
        regions = args[2] if len(args) > 2 else "MO,SPB"
        await message.answer(f"🌍 Запускаю OSM-импорт по регионам: {html_std.escape(regions)}…")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "tools/parsers/osm_banyas.py", "--regions", regions,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
            payload = (out or err).decode("utf-8", errors="replace")[-1500:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("OSM-импорт не уложился в 2 минуты.")
        except Exception as e:
            return await message.answer(f"OSM-импорт упал: {e}")

    if sub == "hidenoise":
        cmd_args = ["python3", "-u", "tools/banya_hide_noise.py"]
        rest = args[2:]
        if "--apply" in rest:
            cmd_args.append("--apply")
            rest = [a for a in rest if a != "--apply"]
        for tok in rest:
            if tok.upper() in {"MO", "SPB", "MSK", "LO"}:
                cmd_args += ["--region", tok.upper()]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            payload = (out or b"").decode("utf-8", errors="replace")
            if len(payload) > 3600:
                payload = payload[:2400] + "\n…(…)…\n" + payload[-1100:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>", parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("hidenoise: таймаут 1 мин.")
        except Exception as e:
            return await message.answer(f"hidenoise: {e}")

    if sub == "pubauto":
        cmd_args = ["python3", "-u", "tools/banya_pubauto.py"]
        rest = args[2:]
        apply_mode = "--apply" in rest
        if apply_mode:
            cmd_args.append("--apply")
            rest = [a for a in rest if a != "--apply"]
        # --dry — синоним dry-run (по умолчанию dry)
        rest = [a for a in rest if a != "--dry"]
        nums: list[str] = []
        for tok in rest:
            up = tok.upper()
            if up in {"MO", "SPB", "MSK", "LO"}:
                cmd_args += ["--region", up]
                continue
            try:
                float(tok)
                nums.append(tok)
            except ValueError:
                continue
        if nums:
            cmd_args += ["--min-rating", nums[0]]
        if len(nums) >= 2:
            cmd_args += ["--min-reviews", str(int(float(nums[1])))]
        if len(nums) >= 3:
            cmd_args += ["--limit", str(int(float(nums[2])))]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            payload = (out or b"").decode("utf-8", errors="replace")
            if len(payload) > 3600:
                payload = payload[:2400] + "\n…(…)…\n" + payload[-1100:]
            mode = "APPLY" if apply_mode else "DRY"
            return await message.answer(
                f"<b>pubauto · {mode}</b>\n<pre>{html_std.escape(payload)}</pre>",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("pubauto: таймаут 2 мин.")
        except Exception as e:
            return await message.answer(f"pubauto: {e}")

    if sub == "moderateai":
        cmd_args = ["python3", "-u", "tools/banya_review_moderate_ai.py", *args[2:]]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=420)
            payload = (out or b"").decode("utf-8", errors="replace")
            if len(payload) > 3800:
                payload = payload[:2600] + "\n…(…)…\n" + payload[-1100:]
            return await message.answer(
                f"<b>moderateai</b> <code>rc={proc.returncode}</code>\n<pre>{html_std.escape(payload)}</pre>",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("moderateai: таймаут 7 мин (эмбеддинги + API).")
        except Exception as e:
            return await message.answer(f"moderateai: {e}")

    if sub == "refresh":
        if len(args) < 3:
            return await message.answer(
                "Формат: /banya refresh <id|region> [limit] [needreviews]\n"
                "Например: /banya refresh MO 60 · /banya refresh MO 200 needreviews · /banya refresh 11"
            )
        target = args[2]
        limit = "50"
        need_reviews = False
        for tok in args[3:]:
            tl = tok.lower()
            if tok.isdigit():
                limit = tok
            elif tl in ("needreviews", "noreviews", "0rev"):
                need_reviews = True
        cmd_args = ["python3", "-u", "tools/parsers/yandex_scrape.py", "refresh"]
        if need_reviews:
            cmd_args.append("--need-reviews")
        if target.upper() in {"MO", "SPB", "MSK", "LO"}:
            cmd_args += ["--region", target.upper(), "--limit", limit]
        elif target.isdigit():
            cmd_args += ["--id", target]
        else:
            return await message.answer("Нужен id (число) или код региона (MO/SPB/MSK/LO).")
        await message.answer("↻ Освежаю rating/reviews по уже привязанным…")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=60 * 120)
            payload = (out or b"").decode("utf-8", errors="replace")[-2500:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>", parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("refresh: таймаут 2 ч.")
        except Exception as e:
            return await message.answer(f"refresh: {e}")

    if sub in ("dups", "dedupe"):
        apply = sub == "dedupe"
        cmd = ["python3", "-u", "tools/banya_dedupe.py"]
        cmd.append("--apply" if apply else "--show")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            payload = (out or b"").decode("utf-8", errors="replace")
            # TG limit 4096; режем, оставляя голову + последнюю строку
            if len(payload) > 3600:
                head = payload[:2400]
                tail_str = payload[-1100:]
                payload = head + "\n…(…)…\n" + tail_str
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>", parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("dedupe: таймаут 2 мин.")
        except Exception as e:
            return await message.answer(f"dedupe: {e}")

    if sub == "report":
        await message.answer("Собираю утренний отчёт…")
        try:
            body = await _build_banya_morning_report()
            await message.answer(
                body,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception as e:
            await message.answer(f"report упал: {e}")
        return

    if sub == "daily":
        await message.answer(
            "🌙 Запускаю <code>yandex_scrape daily</code> (enrich + reviews, лимиты из env)…",
            parse_mode="HTML",
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "tools/parsers/yandex_scrape.py", "daily",
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=3600)
            payload = (out or err or b"").decode("utf-8", errors="replace")[-2500:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("Daily: таймаут 1 ч.")
        except Exception as e:
            return await message.answer(f"Daily: {e}")

    if sub == "enrich":
        if len(args) < 3:
            return await message.answer(
                "Формат: /banya enrich <id|region> [limit]\n"
                "Например: /banya enrich 11 · /banya enrich MO 20"
            )
        target = args[2]
        limit = args[3] if len(args) > 3 else "20"
        cmd = ["python3", "tools/parsers/yandex_scrape.py", "enrich"]
        if target.upper() in {"MO", "SPB", "MSK", "LO"}:
            cmd += ["--region", target.upper(), "--limit", limit]
        elif target.isdigit():
            cmd += ["--id", target]
        else:
            return await message.answer("Нужен id (число) или код региона (MO/SPB/MSK/LO).")
        await message.answer("🔎 Запускаю Яндекс-обогащение… это может занять несколько минут.")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=60 * 30)
            payload = (out or err).decode("utf-8", errors="replace")[-2500:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("Enrich превысил лимит 30 минут.")
        except Exception as e:
            return await message.answer(f"Enrich упал: {e}")

    if sub == "reviews":
        if len(args) < 3:
            return await message.answer(
                "Формат: /banya reviews <id> [max]\n"
                "Например: /banya reviews 11 · /banya reviews 11 10"
            )
        sid = args[2]
        max_rv = args[3] if len(args) > 3 else "8"
        if not sid.isdigit():
            return await message.answer("Нужен числовой id бани.")
        await message.answer(f"📝 Снимаем отзывы с Яндекса для #{sid}…")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "tools/parsers/yandex_scrape.py", "reviews",
                "--id", sid, "--max", max_rv,
                cwd=str(EMPIRE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
            payload = (out or err).decode("utf-8", errors="replace")[-2500:]
            return await message.answer(
                f"<pre>{html_std.escape(payload)}</pre>\n\nПросмотр: /banya pending",
                parse_mode="HTML",
            )
        except asyncio.TimeoutError:
            return await message.answer("Reviews не уложился в 5 минут.")
        except Exception as e:
            return await message.answer(f"Reviews упал: {e}")

    if sub == "pending":
        page = 1
        if len(args) > 2 and args[2].isdigit():
            page = max(1, int(args[2]))
        page_size = 5
        offset = (page - 1) * page_size
        async with async_session() as session:
            stmt_total = select(BanyaReview).where(BanyaReview.status == "pending")
            res_total = await session.execute(stmt_total)
            total = len(list(res_total.scalars().all()))
            stmt = (
                select(BanyaReview, BanyaSpot)
                .join(BanyaSpot, BanyaSpot.id == BanyaReview.spot_id)
                .where(BanyaReview.status == "pending")
                .order_by(BanyaReview.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            res = await session.execute(stmt)
            rows = list(res.all())
        if not rows:
            return await message.answer(f"Отзывов на модерации нет (всего pending: {total}).")
        for rv, sp in rows:
            text_short = (rv.text or "")[:600]
            stars = "★" * (rv.rating or 0) + "☆" * (5 - (rv.rating or 0)) if rv.rating else "—"
            body = (
                f"<b>#{rv.id}</b> · спот <code>#{sp.id}</code> {html_std.escape(sp.title or '?')}\n"
                f"<i>{html_std.escape(rv.author or 'аноним')}</i> · {stars}\n\n"
                f"{html_std.escape(text_short)}"
            )
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="✅ Approve", callback_data=f"rv_ok:{rv.id}"
                ),
                types.InlineKeyboardButton(
                    text="🚫 Hide", callback_data=f"rv_no:{rv.id}"
                ),
            ]])
            await message.answer(body, parse_mode="HTML", reply_markup=kb)
        footer = f"Страница {page}/{(total + page_size - 1) // page_size} · всего pending: {total}"
        nav = []
        if (offset + page_size) < total:
            nav.append(f"/banya pending {page + 1}")
        if page > 1:
            nav.append(f"/banya pending {page - 1}")
        if nav:
            footer += "\n" + " · ".join(nav)
        return await message.answer(footer)

    if sub in ("approve", "rhide"):
        if len(args) < 3 or not args[2].isdigit():
            return await message.answer(f"Формат: /banya {sub} <review_id>")
        rv_id = int(args[2])
        new_status = "approved" if sub == "approve" else "hidden"
        async with async_session() as session:
            rv = await session.get(BanyaReview, rv_id)
            if not rv:
                return await message.answer("Отзыв не найден.")
            rv.status = new_status
            await session.commit()
            # Пересчитаем счётчики у спота
            cnt = (await session.execute(
                select(func.count()).select_from(BanyaReview)
                .where(BanyaReview.spot_id == rv.spot_id,
                       BanyaReview.status == "approved")
            )).scalar() or 0
            sp = await session.get(BanyaSpot, rv.spot_id)
            if sp:
                sp.reviews_total = cnt
                sp.updated_at = datetime.utcnow()
                await session.commit()
        return await message.answer(
            f"{'✅' if new_status == 'approved' else '🚫'} Отзыв #{rv_id} → {new_status}"
        )

    if sub == "approvebulk":
        apply_bulk = False
        min_rating = 1
        min_text = 10
        limit_n = 0
        source_f: str | None = None
        require_rating = False
        i = 2
        while i < len(args):
            tok = args[i]
            if tok == "--apply":
                apply_bulk = True
                i += 1
            elif tok == "--require-rating":
                require_rating = True
                i += 1
            elif tok == "--min-rating" and i + 1 < len(args) and args[i + 1].lstrip("-").isdigit():
                min_rating = int(args[i + 1])
                i += 2
            elif tok == "--min-text" and i + 1 < len(args) and args[i + 1].isdigit():
                min_text = int(args[i + 1])
                i += 2
            elif tok == "--limit" and i + 1 < len(args) and args[i + 1].isdigit():
                limit_n = int(args[i + 1])
                i += 2
            elif tok == "--source" and i + 1 < len(args):
                source_f = args[i + 1].strip()
                i += 2
            else:
                return await message.answer(
                    "Формат: <code>/banya approvebulk [--apply] [--min-rating 3] [--min-text 10] "
                    "[--limit 200] [--source yandex] [--require-rating]</code>\n"
                    "Без <code>--apply</code> — только список кандидатов (dry-run).",
                    parse_mode="HTML",
                )
        text_len = func.length(func.trim(BanyaReview.text))
        conds = [
            BanyaReview.status == "pending",
            text_len >= min_text,
        ]
        if source_f:
            conds.append(BanyaReview.source == source_f)
        if require_rating:
            conds.append(and_(BanyaReview.rating.isnot(None), BanyaReview.rating >= min_rating))
        else:
            conds.append(or_(BanyaReview.rating.is_(None), BanyaReview.rating >= min_rating))
        bulk_stmt = (
            select(BanyaReview)
            .where(and_(*conds))
            .order_by(BanyaReview.id.asc())
        )
        if limit_n > 0:
            bulk_stmt = bulk_stmt.limit(limit_n)
        async with async_session() as session:
            res = await session.execute(bulk_stmt)
            rows = list(res.scalars().all())
        if not rows:
            rating_desc = (
                f"только с оценкой ≥{min_rating}"
                if require_rating
                else f"без оценки или ≥{min_rating}"
            )
            src = f", source={html_std.escape(source_f)}" if source_f else ""
            return await message.answer(
                f"Нет кандидатов (pending, текст ≥{min_text} симв., рейтинг {rating_desc}{src}).",
                parse_mode="HTML",
            )
        prev = "\n".join(
            f"<code>#{r.id}</code> spot={r.spot_id} ★{r.rating if r.rating is not None else '—'} "
            f"{html_std.escape((r.text or '')[:72])}"
            for r in rows[:12]
        )
        if len(rows) > 12:
            prev += f"\n… и ещё <b>{len(rows) - 12}</b>"
        head = (
            f"<b>approvebulk</b> кандидатов: <b>{len(rows)}</b> "
            f"(min_text={min_text}, min_rating={min_rating}, apply={apply_bulk})\n\n{prev}"
        )
        if not apply_bulk:
            head += "\n\n<i>Повтори с --apply чтобы одобрить.</i>"
            return await message.answer(head, parse_mode="HTML")
        spot_ids: set[int] = set()
        async with async_session() as session:
            res2 = await session.execute(bulk_stmt)
            for rv in res2.scalars().all():
                rv.status = "approved"
                spot_ids.add(int(rv.spot_id))
            await session.commit()
            for sid in sorted(spot_ids):
                cnt = (
                    await session.execute(
                        select(func.count())
                        .select_from(BanyaReview)
                        .where(
                            BanyaReview.spot_id == sid,
                            BanyaReview.status == "approved",
                        )
                    )
                ).scalar() or 0
                sp = await session.get(BanyaSpot, sid)
                if sp:
                    sp.reviews_total = cnt
                    sp.updated_at = datetime.utcnow()
            await session.commit()
        return await message.answer(
            head + f"\n\n✅ Одобрено: <b>{len(rows)}</b>, затронуто спотов: <b>{len(spot_ids)}</b>",
            parse_mode="HTML",
        )

    if sub == "draft":
        # /banya draft               -> страница 1, все регионы
        # /banya draft MO            -> только МО, страница 1
        # /banya draft MO 2          -> МО страница 2
        region = None
        page = 1
        for a in args[2:4]:
            if a.upper() in {"MO", "SPB", "MSK", "LO"}:
                region = a.upper()
            elif a.isdigit():
                page = max(1, int(a))
        page_size = 20
        offset = (page - 1) * page_size
        async with async_session() as session:
            stmt = select(BanyaSpot).where(BanyaSpot.status == "draft")
            if region:
                stmt = stmt.where(BanyaSpot.region == region)
            stmt = stmt.order_by(BanyaSpot.region, BanyaSpot.city, BanyaSpot.title)
            res = await session.execute(stmt)
            all_spots = list(res.scalars().all())
        total = len(all_spots)
        page_spots = all_spots[offset:offset + page_size]
        if not page_spots:
            return await message.answer(
                f"Черновиков нет (region={region or 'all'}, page={page}). Всего: {total}."
            )
        header = (
            f"<b>Черновики</b>: {total}"
            + (f" · region={region}" if region else "")
            + f" · page {page}/{(total + page_size - 1) // page_size}"
        )
        lines = [header, ""]
        for s in page_spots:
            city_part = f"{html_std.escape(s.city or '—')}"
            reg_part = f"[{s.region or '?'}]"
            lines.append(
                f"🟡 <code>#{s.id}</code> {reg_part} {city_part} · "
                f"<b>{html_std.escape(s.title or '?')}</b>"
            )
        hint_parts = []
        if (offset + page_size) < total:
            hint_parts.append(f"/banya draft {region or ''} {page + 1}".strip())
        if page > 1:
            hint_parts.append(f"/banya draft {region or ''} {page - 1}".strip())
        if hint_parts:
            lines.append("")
            lines.append("Дальше: " + " · ".join(hint_parts))
        lines.append("Опубликовать: /banya pub <id>")
        return await message.answer("\n".join(lines), parse_mode="HTML")

    if sub in ("pub", "hide", "info", "visited", "clip", "clips", "clipdel"):
        if len(args) < 3:
            return await message.answer("Нужен id или slug бани.")
        ref = args[2]
        async with async_session() as session:
            spot = await _find_banya(session, ref)
            if not spot:
                return await message.answer(f"Не нашёл баню «{ref}»")

            if sub == "info":
                tags = []
                try:
                    tags = json.loads(spot.tags_json or "[]")
                except Exception:
                    pass
                clips = normalize_clip_list(spot.clips_json)
                providers = {}
                for c in clips:
                    providers[c.get("provider", "?")] = providers.get(c.get("provider", "?"), 0) + 1
                lines = [
                    f"{_banya_status_icon(spot.status)} <b>{html_std.escape(spot.title or '?')}</b>",
                    f"slug=<code>{html_std.escape(spot.slug or '')}</code> · id=#{spot.id}",
                    f"{html_std.escape(spot.city or '?')} · {html_std.escape(spot.address or '')}",
                    f"тип: {html_std.escape(spot.kind or '?')}, нагрев: {html_std.escape(spot.heating or '?')}",
                    f"визит: {'был лично' if spot.visited else 'не были'}",
                    f"теги: {', '.join(tags) if tags else '—'}",
                    f"клипы: {len(clips)}"
                    + (f" ({', '.join(f'{k}:{v}' for k, v in providers.items())})" if providers else ""),
                ]
                if spot.site_url:
                    lines.append(f"сайт: {html_std.escape(spot.site_url)}")
                if spot.phone:
                    lines.append(f"тел: {html_std.escape(spot.phone)}")
                if spot.description:
                    lines.append("")
                    lines.append(html_std.escape(spot.description[:600]))
                return await message.answer("\n".join(lines), parse_mode="HTML")

            if sub == "clips":
                clips = normalize_clip_list(spot.clips_json)
                if not clips:
                    return await message.answer("Клипов пока нет.")
                lines = [f"<b>Клипы</b> «{html_std.escape(spot.title or '?')}»:"]
                for i, c in enumerate(clips):
                    title = html_std.escape(c.get("title", "") or "")
                    title_part = f" · {title}" if title else ""
                    lines.append(
                        f"<code>{i}</code> [{c.get('provider', '?')}] "
                        f"{html_std.escape(c.get('url', ''))}{title_part}"
                    )
                return await message.answer("\n".join(lines), parse_mode="HTML",
                                             disable_web_page_preview=True)

            if sub == "pub":
                spot.status = "published"
            elif sub == "hide":
                spot.status = "hidden"
            elif sub == "visited":
                flag = (args[3].lower() if len(args) > 3 else "on") == "on"
                spot.visited = 1 if flag else 0
            elif sub == "clip":
                if len(args) < 4:
                    return await message.answer(
                        "Формат: /banya clip <id|slug> <url> [подпись...]\n"
                        "Принимаем: VK Video/Clips, Rutube, YouTube (бэкап), Telegram-пост, прямой mp4."
                    )
                raw_url = args[3]
                clip = parse_video_clip(raw_url)
                if not clip:
                    return await message.answer(
                        "Не распознал источник. Поддерживаются: VK Video/Clips, Rutube, "
                        "YouTube, Telegram-пост, прямые .mp4/.webm/.mov."
                    )
                if len(args) > 4:
                    clip["title"] = " ".join(args[4:])
                clips = normalize_clip_list(spot.clips_json)
                clips.append(clip)
                spot.clips_json = json.dumps(clips, ensure_ascii=False)
            elif sub == "clipdel":
                if len(args) < 4:
                    return await message.answer("Формат: /banya clipdel <id|slug> <index>")
                try:
                    idx = int(args[3])
                except Exception:
                    return await message.answer("index должен быть числом.")
                clips = normalize_clip_list(spot.clips_json)
                if not (0 <= idx < len(clips)):
                    return await message.answer(
                        f"index вне диапазона 0..{len(clips) - 1 if clips else 0}"
                    )
                removed = clips.pop(idx)
                spot.clips_json = json.dumps(clips, ensure_ascii=False)
                spot.updated_at = datetime.utcnow()
                await session.commit()
                return await message.answer(
                    f"Удалил клип [{removed.get('provider', '?')}] {removed.get('url', '')}"
                )

            spot.updated_at = datetime.utcnow()
            await session.commit()

            if sub == "clip":
                return await message.answer(
                    f"OK: #{spot.id} ({spot.slug}) → +клип [{clip.get('provider')}] "
                    f"всего {len(normalize_clip_list(spot.clips_json))}"
                )
            return await message.answer(f"OK: #{spot.id} ({spot.slug}) → {sub}")

    return await message.answer("Неизвестная подкоманда. Смотри /banya без аргументов.")


@dp.message(Command("critique"))
async def cmd_critique(message: types.Message):
    """Прогнать self-critique по существующему черновику: /critique <draft_id>"""
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Формат: /critique <draft_id>")
    try:
        d_id = int(args[1])
    except Exception:
        return await message.answer("draft_id должен быть числом.")

    async with async_session() as session:
        draft = await session.get(PostDraft, d_id)
        if not draft:
            return await message.answer(f"Черновик #{d_id} не найден.")
        p_key = draft.persona_key
        text = draft.text_content or ""
        topic = draft.topic_raw or "(тема не сохранена)"

    persona = PERSONAS.get(p_key)
    if not persona:
        return await message.answer(f"Неизвестная персона: {p_key}")

    findings = _selfcritique_findings(p_key, text)
    if not findings:
        return await message.answer(f"#{d_id} [{p_key}]: критика не нашла проблем. Пост можно публиковать.")

    rewritten = await _selfcritique_rewrite(p_key, persona, topic, text, findings)
    if not rewritten:
        return await message.answer(
            f"#{d_id} [{p_key}]: критика нашла {len(findings)} проблем(ы), но переписать не удалось.\n"
            + "\n".join(f"• {f}" for f in findings)
        )

    candidate = fix_html_safety(rewritten)
    if p_key == "stern":
        candidate = _apply_stern_typos(candidate)
    rubric_match = re.match(r"\[(.*?)\]", topic)
    rubric_plain = rubric_match.group(1).strip() if rubric_match else None
    is_pension_video = p_key == "pension" and "видео" in topic.lower()
    candidate = finalize_public_post(candidate, p_key, rubric_plain, is_pension_video)
    new_findings = _selfcritique_findings(p_key, candidate)
    if len(new_findings) >= len(findings):
        return await message.answer(
            f"#{d_id} [{p_key}]: переписка не уменьшила число проблем "
            f"({len(findings)} → {len(new_findings)}). Оставляю старый текст."
        )

    async with async_session() as session:
        d = await session.get(PostDraft, d_id)
        if d:
            d.text_content = candidate
            await session.commit()

    summary = "\n".join(f"• {f}" for f in findings)
    await message.answer(
        f"#{d_id} [{p_key}]: переписано. Проблем было {len(findings)} → {len(new_findings)}.\n{summary}"
    )
    await notify_admin(d_id, p_key, candidate, (await _get_draft_image_path(d_id)))


async def _get_draft_image_path(d_id: int) -> str | None:
    async with async_session() as session:
        d = await session.get(PostDraft, d_id)
        return d.image_path if d else None


def _append_to_blacklist(p_key: str, basename: str) -> None:
    path = f"media/{p_key}/pool/.blacklist.txt"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        existing: set[str] = set()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for ln in fh:
                    s = ln.strip()
                    if s and not s.startswith("#"):
                        existing.add(s)
        if basename in existing:
            return
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(basename + "\n")
        # сбрасываем кеш
        _BLACKLIST_CACHE.clear()
    except Exception as e:
        logger.warning(f"[blacklist] append error: {e}")


@dp.callback_query(F.data.startswith("badimg_"))
async def cb_badimg(callback: CallbackQuery):
    d_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        res = await session.execute(select(PostDraft).where(PostDraft.id == d_id))
        draft = res.scalar_one_or_none()
        if not draft or draft.persona_key in ["pension", "lenin"]:
            await callback.answer("Нельзя для этой персоны.", show_alert=True)
            return

        # Имя файла-источника, из которого мы СКОПИРОВАЛИ в draft_<id>.jpg, мы храним
        # в нашем сервис-логе. Здесь восстановим базовое имя из пула: смотрим
        # последний выбранный файл по imghash-совпадению.
        cur_path = draft.image_path
        bad_basename = None
        if cur_path and os.path.exists(cur_path):
            try:
                with open(cur_path, "rb") as fh:
                    cur_bytes = fh.read()
                pool_dir = f"media/{draft.persona_key}/pool"
                if os.path.isdir(pool_dir):
                    for f in os.listdir(pool_dir):
                        if f.startswith("."):
                            continue
                        p = os.path.join(pool_dir, f)
                        if not os.path.isfile(p):
                            continue
                        try:
                            if os.path.getsize(p) == len(cur_bytes):
                                with open(p, "rb") as fh2:
                                    if fh2.read() == cur_bytes:
                                        bad_basename = f
                                        break
                        except Exception:
                            continue
            except Exception:
                pass

        if bad_basename:
            _append_to_blacklist(draft.persona_key, bad_basename)
            await callback.answer(f"В корзину: {bad_basename[:40]}…", show_alert=False)
        else:
            await callback.answer("Картинка не из пула (или уже заменена) — просто перегенерирую.", show_alert=False)

        new_img = await generate_image(
            draft.image_prompt,
            d_id,
            draft.persona_key,
            topic_hint=draft.image_prompt,
            topic_raw=draft.topic_raw,
        )
        draft.image_path = new_img
        draft.bad_image_count = (draft.bad_image_count or 0) + 1
        await session.commit()
        try:
            await callback.message.delete()
        except Exception:
            pass
        await notify_admin(d_id, draft.persona_key, draft.text_content, new_img)


@dp.callback_query(F.data.startswith("curimg_"))
async def cb_curimg(callback: CallbackQuery):
    """Curated-рубрики: другой выпуск (цитата + портрет/плакат/кадр с Commons)."""
    d_id = int(callback.data.split("_")[1])
    await callback.answer("⏳ Подбираю другое фото и текст рубрики…", show_alert=False)
    from rubric_posts import curated_resample

    async with async_session() as session:
        res = await session.execute(select(PostDraft).where(PostDraft.id == d_id))
        draft = res.scalar_one_or_none()
        if not draft:
            return await callback.answer("Черновик не найден.", show_alert=True)
        if not _curated_rubric_requires_photo(draft.persona_key, draft.topic_raw):
            return await callback.answer("Только для curated-рубрик.", show_alert=True)
        sampled = await curated_resample(draft.persona_key, draft.topic_raw or "")
        if not sampled:
            return await callback.answer("Не удалось сменить выпуск рубрики.", show_alert=True)
        topic, text, img = sampled
        draft.topic_raw = topic
        draft.text_content = text
        draft.image_path = img
        draft.regen_count = (draft.regen_count or 0) + 1
        await session.commit()
        try:
            await callback.message.delete()
        except Exception:
            pass
        await notify_admin(d_id, draft.persona_key, text, img, topic_raw=topic)


@dp.callback_query(F.data.startswith("regen_"))
async def cb_regen(callback: CallbackQuery):
    d_id = int(callback.data.split("_")[1])
    await callback.answer("⏳ Перегенерирую картинку...", show_alert=False)
    
    async with async_session() as session:
        res = await session.execute(select(PostDraft).where(PostDraft.id == d_id))
        draft = res.scalar_one_or_none()
        if draft and _curated_rubric_requires_photo(draft.persona_key, draft.topic_raw):
            return await callback.answer(
                "Для рубрики используйте «🖼 Другая картинка».", show_alert=True
            )
        if draft and draft.persona_key not in ["pension", "lenin"]:
            # Стабильный topic_hint — английский image_prompt (он создан из исходной темы).
            # Так регенерация остаётся в той же ветке STERN_TOPIC_RULES, что и первый прогон.
            new_img = await generate_image(
                draft.image_prompt,
                d_id,
                draft.persona_key,
                topic_hint=draft.image_prompt,
                topic_raw=draft.topic_raw,
            )
            if draft.persona_key == "gdepar" and gdepar_content:
                canon = gdepar_content.resolve_gdepar_image_prompt(
                    _image_hints_for_venik(draft.topic_raw, draft.image_prompt)
                )
                if canon:
                    draft.image_prompt = canon
            draft.image_path = new_img
            draft.regen_count = (draft.regen_count or 0) + 1
            await session.commit()
            await callback.message.delete()
            await notify_admin(d_id, draft.persona_key, draft.text_content, new_img)

async def _publish_extra_channels(draft: PostDraft) -> None:
    """VK / Дзен RSS после успешной публикации в TG (empire_publish_channels)."""
    from empire_publish import publish_draft_multi
    from empire_publish_channels import channels_for_persona

    extra = [c for c in channels_for_persona(draft.persona_key) if c != "tg"]
    if not extra:
        return
    try:
        async with async_session() as session:
            results = await publish_draft_multi(
                session,
                content_id=draft.id,
                channels=extra,
                persona_key=draft.persona_key,
            )
        for res in results:
            if not res.ok:
                logger.warning(
                    "[publish] extra channel %s failed #%s: %s",
                    res.channel,
                    draft.id,
                    res.detail,
                )
    except Exception as exc:
        logger.warning("[publish] extra channels error #%s: %s", draft.id, exc)


@dp.callback_query(F.data.startswith("send_"))
async def cb_send(callback: CallbackQuery):
    d_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        res = await session.execute(select(PostDraft).where(PostDraft.id == d_id))
        draft = res.scalar_one_or_none()
        if draft:
            if _curated_rubric_requires_photo(
                draft.persona_key, draft.topic_raw
            ) and not _curated_has_photo(draft.image_path):
                return await callback.answer(
                    "Рубрика: нужна картинка. Prefetch на сервере, затем approve.",
                    show_alert=True,
                )
            p0 = (
                content_p0.p0_findings(draft.text_content or "", draft.persona_key)
                if content_p0
                else []
            )
            if p0:
                return await callback.answer(
                    f"P0 брак — не публиковать:\n{p0[0][:180]}",
                    show_alert=True,
                )
            ok, err_hint, msg_id = await _send_draft_to_channel(draft)
            if ok:
                draft.status = "published"
                draft.decision = "approved"
                draft.decided_at = datetime.utcnow()
                await session.commit()
                await _publish_extra_channels(draft)
                if draft.persona_key == "stern" and msg_id:
                    import stern_week_arc as swa

                    swa.mark_post_published(draft.id, msg_id)
                _record_stern_technique_if_published(draft)
                _record_stern_comic_if_published(draft)
                await callback.answer("🚀 Опубликовано!")
                await callback.message.edit_reply_markup(reply_markup=None)
            else:
                msg = err_hint or "Не удалось отправить в канал."
                await callback.answer(msg[:190], show_alert=True)

@dp.callback_query(F.data.startswith("delete_"))
async def cb_delete(callback: CallbackQuery):
    try:
        d_id = int(callback.data.split("_")[1])
    except Exception:
        d_id = None
    if d_id is not None:
        async with async_session() as session:
            res = await session.execute(select(PostDraft).where(PostDraft.id == d_id))
            draft = res.scalar_one_or_none()
            if draft:
                draft.status = "rejected"
                draft.decision = "rejected"
                draft.decided_at = datetime.utcnow()
                await session.commit()
    await callback.message.delete()
    await callback.answer("Черновик удалён.")


@dp.callback_query(F.data.startswith("rv_"))
async def cb_review_moderate(callback: CallbackQuery):
    """Approve/Hide для отзыва из /banya pending."""
    try:
        action, rid = callback.data.split(":", 1)
        rid = int(rid)
    except Exception:
        return await callback.answer("Bad callback")
    new_status = "approved" if action == "rv_ok" else "hidden"
    async with async_session() as session:
        rv = await session.get(BanyaReview, rid)
        if not rv:
            return await callback.answer("Отзыв не найден.", show_alert=True)
        rv.status = new_status
        await session.commit()
        cnt = (await session.execute(
            select(func.count()).select_from(BanyaReview)
            .where(BanyaReview.spot_id == rv.spot_id,
                   BanyaReview.status == "approved")
        )).scalar() or 0
        sp = await session.get(BanyaSpot, rv.spot_id)
        if sp:
            sp.reviews_total = cnt
            sp.updated_at = datetime.utcnow()
            await session.commit()
    badge = "✅ approved" if new_status == "approved" else "🚫 hidden"
    try:
        # подменим клавиатуру на «решение принято»
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.edit_text(
            (callback.message.html_text or callback.message.text or "") + f"\n\n<i>→ {badge}</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer(badge)


async def _dispatch_obsidian_entry(entry: dict) -> int | None:
    """Вариант A: одна заметка из очереди → PostDraft → approve в Telegram."""
    import obsidian_content as oc

    eid = entry.get("id")
    if not eid:
        return None
    p_key = (entry.get("persona") or "pension").strip().lower()
    topic = oc.topic_raw_for_entry(entry)
    text = oc.build_post_html(entry, fix_html_fn=fix_html_safety, finalize_fn=finalize_public_post)

    async with async_session() as session:
        draft = PostDraft(
            persona_key=p_key,
            text_content=text,
            image_prompt=entry.get("image_prompt") or "",
            topic_raw=topic,
            decision="pending",
        )
        session.add(draft)
        await session.commit()
        d_id = draft.id

    img_f = await oc.resolve_image_path(
        entry, generate_image, d_id, p_key, topic
    )
    async with async_session() as session:
        d = await session.get(PostDraft, d_id)
        d.image_path = img_f
        await session.commit()

    await _record_topic_history(p_key, topic, d_id)
    if entry.get("image") and not img_f:
        try:
            await bot.send_message(
                ADMIN_ID,
                (
                    f"⚠️ <b>Obsidian: нет файла картинки</b>\n"
                    f"{html_std.escape(str(entry.get('title', '')))}\n"
                    f"Ожидается: <code>{html_std.escape(str(entry.get('image', '')))}</code>\n"
                    f"Положите файл в <code>Empire/pension/queue/attachments/</code> на ПК "
                    f"и дождитесь sync Яндекс.Диска — бот подтянет к #{d_id}.\n"
                    f"Черновик без фото: можно опубликовать или /obsidian image {d_id}"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await notify_admin(d_id, p_key, text, img_f, topic_raw=topic)
    oc.mark_dispatched(eid, scheduled=entry.get("scheduled"))
    return d_id


async def check_obsidian_queue():
    """Импорт queue (по интервалу), напоминания и черновики по scheduled."""
    if not ADMIN_ID:
        return
    import obsidian_content as oc

    oc.run_import_if_needed()
    now = datetime.now(MSK_TZ)

    for entry in oc.entries_reminder(now):
        sched = oc.parse_scheduled(entry.get("scheduled"), now=now)
        when = sched.strftime("%d.%m.%Y %H:%M") if sched else "?"
        try:
            await bot.send_message(
                ADMIN_ID,
                (
                    f"⏰ <b>Obsidian (вариант A)</b>\n"
                    f"{entry.get('persona', '')} · <b>{html_std.escape(str(entry.get('title', '')))}</b>\n"
                    f"Публикация в очереди: <b>{when}</b> МСК\n"
                    f"id: <code>{html_std.escape(str(entry.get('id', '')))}</code>"
                ),
                parse_mode="HTML",
            )
            oc.mark_reminded(entry["id"])
        except Exception as exc:
            logger.warning("obsidian reminder failed %s: %s", entry.get("id"), exc)

    for entry in oc.entries_due(now):
        try:
            await _dispatch_obsidian_entry(entry)
        except Exception as exc:
            logger.exception("obsidian dispatch %s: %s", entry.get("id"), exc)
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"Obsidian: не удалось создать черновик {entry.get('id')}: {exc}",
                )
            except Exception:
                pass

    await _refresh_pending_obsidian_images()


async def _refresh_pending_obsidian_images() -> None:
    """Подтянуть картинку к pending Obsidian-черновикам, если файл появился после sync."""
    import obsidian_content as oc

    async with async_session() as session:
        res = await session.execute(
            select(PostDraft).where(
                PostDraft.status == "pending",
                PostDraft.topic_raw.like("[Obsidian]%"),
            )
        )
        drafts = res.scalars().all()
        for draft in drafts:
            if draft.image_path and os.path.isfile(draft.image_path):
                continue
            img_f = await oc.resolve_image_for_topic_raw(
                draft.topic_raw, generate_image, draft.id, draft.persona_key
            )
            if not img_f:
                continue
            draft.image_path = img_f
            await session.commit()
            try:
                await notify_admin(
                    draft.id,
                    draft.persona_key,
                    draft.text_content,
                    img_f,
                    topic_raw=draft.topic_raw,
                )
            except Exception as exc:
                logger.warning("obsidian image refresh notify #%s: %s", draft.id, exc)


async def check_scheduler():
    import scheduler_slots as sched_guard

    now = msk_now()
    time_str = now.strftime("%H:%M")
    day_idx = str(now.weekday())

    for p_key, cfg in CONTENT_CONFIG.items():
        if time_str in cfg.get("schedule", []):
            if sched_guard.already_fired(p_key, now, time_str):
                continue
            topics_cfg = cfg.get("topics", {})

            if p_key == "stern" and time_str == "15:00":
                day_bucket = (
                    topics_cfg.get(day_idx)
                    if isinstance(topics_cfg.get(day_idx), dict)
                    else {}
                )
                if time_str not in day_bucket:
                    continue

            if day_idx in topics_cfg and isinstance(topics_cfg.get(day_idx), dict):
                day_bucket = topics_cfg[day_idx]
                if time_str in day_bucket:
                    raw_slot = day_bucket[time_str]
                elif time_str in topics_cfg and not isinstance(topics_cfg.get(time_str), dict):
                    raw_slot = topics_cfg[time_str]
                else:
                    raw_slot = "Свободная тема"
            elif time_str in topics_cfg:
                raw_slot = topics_cfg.get(time_str, "Свободная тема")
            else:
                raw_slot = "Свободная тема"

            topic, prebuilt, prebuilt_img, rubric_seed = await _resolve_scheduled_slot(
                p_key, raw_slot, when=now
            )

            # Скаут — общий, держит свежие заголовки для всех «новостных» персон.
            # Запускаем не чаще раза в час (file mtime), чтобы не дёргать RSS на каждый слот.
            if p_key in ("pension", "gdepar", "garden", "lenin"):
                await _refresh_scout_if_stale(max_age_sec=3600)

            if prebuilt:
                text, img_p = prebuilt, ""
                if rubric_seed and rubric_seed.get("image_prompt_en"):
                    img_p = str(rubric_seed["image_prompt_en"])
                if p_key == "gdepar" and "[SPECIAL:promo_map]" in topic:
                    analytics_log_event(
                        "tg_promo_map_draft",
                        persona_key="gdepar",
                        payload={"topic": topic, "utm": "utm_source=telegram&utm_medium=post&utm_campaign=weekly_map"},
                    )
                if p_key == "garden" and "[SPECIAL:bot_promo]" in topic:
                    analytics_log_event(
                        "garden_bot_promo_draft",
                        persona_key="garden",
                        payload={"topic": topic},
                    )
            elif rubric_seed:
                text, img_p = await generate_draft_content(
                    p_key, topic, rubric_seed=rubric_seed
                )
            else:
                text, img_p = await generate_draft_content(p_key, topic)
            
            async with async_session() as session:
                draft = PostDraft(persona_key=p_key, text_content=text, image_prompt=img_p, topic_raw=topic, decision="pending")
                session.add(draft); await session.commit()
                d_id = draft.id

            stern_week_kind = (
                (rubric_seed or {}).get("_kind") if rubric_seed else None
            )
            skip_image = (
                (p_key == "pension" and prebuilt and "[RAW:" in (topic or ""))
                or (p_key == "gdepar" and prebuilt and "[SPECIAL:promo_map]" in (topic or ""))
                or (
                    p_key == "stern"
                    and (
                        (prebuilt and "[Разбор полетов]" in (topic or ""))
                        or                         (prebuilt and "[Техника гирь]" in (topic or ""))
                        or (prebuilt and "[Комик техника]" in (topic or ""))
                        or (stern_week_kind or "").startswith("stern_weekly")
                    )
                )
            )
            if prebuilt_img:
                _pip = (
                    prebuilt_img
                    if os.path.isabs(prebuilt_img)
                    else str(EMPIRE_ROOT / prebuilt_img)
                )
                if os.path.exists(_pip):
                    img_f = _pip
                else:
                    img_f = None
            elif skip_image:
                img_f = None
            elif (
                not img_p
                and p_key == "garden"
                and garden_content
                and "[Лунный календарь]" in (topic or "")
            ):
                img_f = await generate_image(
                    garden_content.LUNAR_IMAGE_PROMPT,
                    d_id,
                    p_key,
                    topic_hint=topic,
                    topic_raw=topic,
                )
            else:
                wiki_hint = img_p
                if rubric_seed and rubric_seed.get("_kind") == "lenin_calendar":
                    wiki_hint = (
                        rubric_seed.get("rag_query")
                        or rubric_seed.get("event_desc")
                        or wiki_hint
                    )
                img_f = (
                    await generate_image(
                        img_p,
                        d_id,
                        p_key,
                        topic_hint=wiki_hint,
                        topic_raw=topic,
                    )
                    if img_p
                    else None
                )
            if p_key == "lenin" and not img_f:
                rag = (rubric_seed or {}).get("rag_query") if rubric_seed else None
                if rag:
                    img_f = await fetch_wikipedia_image(rag, d_id)
                if not img_f:
                    img_f = await fetch_wikipedia_image("Ленин Владимир Ильич", d_id)
            is_curated_prebuilt = (
                (gdepar_content and gdepar_content.CLASSIC_RUBRIC_TAG in (topic or ""))
                or "[Дуэт]" in (topic or "")
                or (rubric_seed or {}).get("_kind") == "stern_curated"
                or (lenin_content and lenin_content.requires_curated_photo(topic or ""))
                or (garden_content and "[Лунный календарь]" in (topic or ""))
            )
            if (
                prebuilt
                and not img_f
                and not skip_image
                and p_key == "lenin"
                and lenin_content
                and lenin_content.requires_curated_photo(topic or "")
            ):
                img_f = await fetch_wikipedia_image("Ленин Владимир Ильич", d_id)
            if prebuilt and not img_f and not skip_image and p_key in ("gdepar", "lenin") and not is_curated_prebuilt:
                img_f = await generate_image(
                    img_p or "Russian banya vintage",
                    d_id,
                    p_key,
                    topic_hint=img_p or topic,
                    topic_raw=topic,
                )
            async with async_session() as session:
                d = await session.get(PostDraft, d_id)
                d.image_path = img_f; await session.commit()

            await _record_topic_history(p_key, topic, d_id)

            if p_key == "stern":
                import stern_week_arc as swa

                if swa.is_valid_scheduled_post_text(text):
                    if rubric_seed and rubric_seed.get("_kind") == "stern_weekly_plan":
                        swa.save_weekly_plan(topic=topic, text=text, draft_id=d_id)
                    elif rubric_seed and rubric_seed.get("_kind") == "stern_weekly_test":
                        swa.save_weekly_test(topic=topic, text=text, draft_id=d_id)
                    else:
                        swa.record_post(
                            topic=topic, text=text, slot_time=time_str, draft_id=d_id
                        )

            sched_guard.mark_fired(p_key, now, time_str, draft_id=d_id, topic=topic)

            cfg_ap = _load_auto_publish_config()
            curated = _curated_rubric_requires_photo(p_key, topic)
            _, rubric_ap = _auto_publish_rules_for(cfg_ap, p_key, topic)
            can_autopublish = bool(cfg_ap.get("enabled")) or bool(
                isinstance(rubric_ap, dict) and rubric_ap.get("enabled")
            )
            persona_autopublish = bool(
                ((cfg_ap.get("personas") or {}).get(p_key) or {}).get("enabled")
            )
            if curated and not persona_autopublish and not (
                isinstance(rubric_ap, dict) and rubric_ap.get("enabled")
            ):
                await notify_admin(d_id, p_key, text, img_f, topic_raw=topic)
            elif cfg_ap.get("scheduled_only", True) and can_autopublish:
                if await _try_auto_publish_scheduled(d_id, p_key, text, img_f, topic_raw=topic):
                    await _notify_admin_auto_compact(d_id, p_key, topic, text, cfg_ap)
                else:
                    await notify_admin(d_id, p_key, text, img_f, topic_raw=topic)
            else:
                await notify_admin(d_id, p_key, text, img_f, topic_raw=topic)

async def task_generate_rss():
    if generate_zen_rss:
        from rss_maker import generate_all_dzen_rss

        await generate_all_dzen_rss()


async def task_media_gc_enqueue():
    """Раз в неделю ставит media_gc в очередь worker."""
    await enqueue_job("media_gc")


async def task_empire_daily_pipeline():
    """Ежедневно: news → spy → neurocomment dry-run + metrics (если worker не стопнут)."""
    from empire_flags import load_empire_flags

    flags = load_empire_flags()
    if flags.get("stop_worker"):
        return
    if flags.get("stop_scout"):
        return
    await enqueue_job("news_ingest")
    if not flags.get("stop_spy"):
        from spy_config import can_run_spy_pipeline

        if can_run_spy_pipeline():
            await enqueue_job("spy_dry_run")
    if not flags.get("stop_neurocomment"):
        await enqueue_job("neurocomment_dry_run")
    await enqueue_job("metrics_snapshot")


async def task_shorts_weekly():
    """Понедельник: пакет сценариев Shorts (только Stern). Spy→draft — вручную из дашборда."""
    await enqueue_job("shorts_scripts", {"personas": ["stern"], "per_persona": 2})
    await enqueue_job("yt_trends", {"persona": "stern"})


async def task_weekly_insights():
    """Воскресенье: файл AI Insights."""
    await enqueue_job("weekly_insights")


async def task_daily_briefing():
    """Ежедневно 08:00 MSK: фокус дня + чеклист + Telegram."""
    from empire_flags import load_empire_flags

    if load_empire_flags().get("stop_worker"):
        return
    await enqueue_job("daily_insights")


_BANYA_DAILY_LOG = EMPIRE_ROOT / "logs" / "banya_daily_last.log"


async def task_banya_maps_daily():
    """Раз в сутки: малый enrich + reviews (Playwright), лимиты — env BANYA_DAILY_*.

    Полный stdout/stderr пишется в logs/banya_daily_last.log — оттуда читает
    утренний отчёт (task_banya_morning_report).
    """
    logger.info("banya_maps_daily: старт")
    _BANYA_DAILY_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-u", "tools/parsers/yandex_scrape.py", "daily",
            cwd=str(EMPIRE_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=3600)
        body = (out or b"").decode("utf-8", errors="replace")
        rc = proc.returncode
        header = (
            f"# banya_maps_daily run\n"
            f"# started: {datetime.now(MSK_TZ).isoformat(timespec='seconds')}\n"
            f"# rc: {rc}\n"
            f"# bytes: {len(body)}\n\n"
        )
        _BANYA_DAILY_LOG.write_text(header + body, encoding="utf-8")
        if rc != 0:
            logger.warning("banya_maps_daily rc=%s (см. %s)", rc, _BANYA_DAILY_LOG)
        else:
            logger.info("banya_maps_daily ok (см. %s)", _BANYA_DAILY_LOG)
    except asyncio.TimeoutError:
        logger.error("banya_maps_daily: timeout 3600s")
        _BANYA_DAILY_LOG.write_text(
            f"# banya_maps_daily TIMEOUT 3600s at "
            f"{datetime.now(MSK_TZ).isoformat(timespec='seconds')}\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.exception("banya_maps_daily: %s", e)
        _BANYA_DAILY_LOG.write_text(
            f"# banya_maps_daily EXCEPTION at "
            f"{datetime.now(MSK_TZ).isoformat(timespec='seconds')}\n{e}\n",
            encoding="utf-8",
        )


async def _build_banya_morning_report() -> str:
    """Текст-отчёт для админа: состояние БД + хвост daily-лога + свежие pending."""
    lines: list[str] = []
    ts = datetime.now(MSK_TZ).strftime("%Y-%m-%d %H:%M %Z")
    lines.append(f"<b>🌅 Утренний отчёт по картам</b> · {ts}")
    lines.append("")
    async with async_session() as session:
        rows = (await session.execute(text(
            "SELECT region, COUNT(*) AS total,"
            " SUM(CASE WHEN yandex_url IS NOT NULL AND TRIM(yandex_url) != '' THEN 1 ELSE 0 END) AS ya,"
            " SUM(CASE WHEN rating_avg IS NOT NULL AND TRIM(rating_avg) != '' THEN 1 ELSE 0 END) AS ra,"
            " SUM(CASE WHEN phone IS NOT NULL AND TRIM(phone) != '' THEN 1 ELSE 0 END) AS ph,"
            " SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS pub"
            " FROM banya_spots GROUP BY region ORDER BY region"
        ))).all()
        without_url = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE (yandex_url IS NULL OR TRIM(yandex_url) = '') AND status != 'hidden'"
        ))).scalar() or 0
        rv_total = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_reviews"
        ))).scalar() or 0
        rv_pending = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_reviews WHERE status = 'pending'"
        ))).scalar() or 0
        rv_approved = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_reviews WHERE status = 'approved'"
        ))).scalar() or 0
        rv_new_recent = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_reviews "
            "WHERE fetched_at >= datetime('now', '-12 hours')"
        ))).scalar() or 0
        rev_miss_rows = (await session.execute(text(
            "SELECT region, COUNT(*) AS cnt FROM banya_spots "
            "WHERE status != 'hidden' "
            "AND yandex_url IS NOT NULL AND TRIM(yandex_url) != '' "
            "AND (reviews_total IS NULL OR reviews_total = 0) "
            "GROUP BY region ORDER BY region"
        ))).all()
        rev_miss_total = (await session.execute(text(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE status != 'hidden' "
            "AND yandex_url IS NOT NULL AND TRIM(yandex_url) != '' "
            "AND (reviews_total IS NULL OR reviews_total = 0)"
        ))).scalar() or 0
    lines.append("<b>Точки бань</b>")
    lines.append("<pre>region  total  url  rate phone pub</pre>")
    for r in rows:
        region, total, ya, ra, ph, pub = r
        lines.append(
            f"<pre>{(region or '?'):6s} {total:5d} {ya:4d} {ra:5d} {ph:5d} {pub:3d}</pre>"
        )
    lines.append(f"Без yandex_url (не hidden): <b>{without_url}</b>")
    lines.append("")
    lines.append(
        "<b>Без reviews_total</b> "
        "(есть Я.Карты, не hidden — пора /banya refresh … needreviews)"
    )
    if rev_miss_total:
        lines.append("<pre>region   cnt</pre>")
        for reg, cnt in rev_miss_rows:
            lines.append(f"<pre>{(reg or '?'):6s} {int(cnt):5d}</pre>")
        lines.append(f"итого: <b>{int(rev_miss_total)}</b>")
    else:
        lines.append("по этому критерию пусто, ок.")
    lines.append("")
    lines.append("<b>Отзывы</b>")
    lines.append(f"всего: {rv_total} · approved: {rv_approved} · pending: <b>{rv_pending}</b>")
    if rv_new_recent:
        lines.append(f"свежих за 12 ч: <b>{rv_new_recent}</b>")
    lines.append("")
    if _BANYA_DAILY_LOG.exists():
        try:
            body = _BANYA_DAILY_LOG.read_text(encoding="utf-8")
            tail = body[-1500:]
            lines.append("<b>Хвост daily-лога</b>")
            lines.append(f"<pre>{html_std.escape(tail)}</pre>")
        except Exception as e:
            lines.append(f"<i>лог daily недоступен: {e}</i>")
    else:
        lines.append("<i>daily-лога нет — ночной прогон не запускался</i>")
    if rv_pending:
        lines.append("")
        lines.append("Модерация: /banya pending")
    return "\n".join(lines)


async def task_banya_morning_report():
    """07:00 МСК: собираем утренний отчёт и шлём админу."""
    if not ADMIN_ID:
        logger.warning("banya_morning_report: ADMIN_ID не задан, пропускаю")
        return
    try:
        body = await _build_banya_morning_report()
        await bot.send_message(
            ADMIN_ID, body,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        logger.info("banya_morning_report: отправлен")
    except Exception as e:
        logger.exception("banya_morning_report: %s", e)
        try:
            await bot.send_message(ADMIN_ID, f"banya_morning_report упал: {e}")
        except Exception:
            pass


async def main():
    await init_db()
    scheduler = AsyncIOScheduler(timezone=MSK_TZ)
    # Cron по минутам MSK — interval от старта процесса мог пропускать 09:30 и др.
    scheduler.add_job(
        check_scheduler,
        "cron",
        minute="*",
        id="content_matrix",
        replace_existing=True,
    )
    scheduler.add_job(
        check_obsidian_queue,
        "cron",
        minute="*",
        id="obsidian_queue",
        replace_existing=True,
    )
    scheduler.add_job(task_generate_rss, "interval", hours=1)
    scheduler.add_job(
        task_banya_maps_daily,
        "cron",
        hour=4,
        minute=35,
        id="banya_maps_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        task_banya_morning_report,
        "cron",
        hour=7,
        minute=0,
        id="banya_morning_report",
        replace_existing=True,
    )
    scheduler.add_job(
        task_media_gc_enqueue,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=20,
        id="media_gc_weekly",
        replace_existing=True,
    )
    scheduler.add_job(
        task_empire_daily_pipeline,
        "cron",
        hour=5,
        minute=10,
        id="empire_daily_pipeline",
        replace_existing=True,
    )
    scheduler.add_job(
        task_shorts_weekly,
        "cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        id="shorts_weekly",
        replace_existing=True,
    )
    scheduler.add_job(
        task_daily_briefing,
        "cron",
        hour=8,
        minute=0,
        id="daily_briefing",
        replace_existing=True,
    )
    scheduler.add_job(
        task_weekly_insights,
        "cron",
        day_of_week="sun",
        hour=8,
        minute=0,
        id="weekly_insights",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("🚀 Оркестратор запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())