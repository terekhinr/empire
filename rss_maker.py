import html
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc

from main import PostDraft

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///empire.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
MSK_TZ = pytz.timezone("Europe/Moscow")

ROOT = Path(__file__).resolve().parent
BOOK_JSON = ROOT / "data" / "book" / "napensiyu_nikogda.json"

RSS_FILE_PATH = os.getenv("EMPIRE_DZEN_RSS_PATH", "media/rss.xml")
PENSION_RSS_PATH = os.getenv("EMPIRE_DZEN_RSS_PENSION_PATH", "media/rss_pension.xml")
SITE_BASE = os.getenv("EMPIRE_CANONICAL_SITE", "https://neverretire.ru").rstrip("/")
RSS_LIMIT = int(os.getenv("EMPIRE_DZEN_RSS_LIMIT", "20"))
PENSION_DZEN_COVER = os.getenv(
    "PENSION_DZEN_RSS_COVER_URL",
    f"{SITE_BASE}/static/logo-neverretire.png",
).strip()

# native-draft — материалы попадают в черновики Студии (удобно на старте)
DZEN_CATEGORIES = (
    "<category>native-draft</category>",
    "<category>format-article</category>",
    "<category>index</category>",
    "<category>comment-all</category>",
)


def _article_link(post: PostDraft) -> str:
    if (post.persona_key or "") == "pension":
        return f"{SITE_BASE}/articles/{post.id}"
    return f"{SITE_BASE}/post/{post.id}"


def _title_from_topic_raw(topic_raw: str | None) -> str | None:
    """longread-01-dzen|Заголовок → Заголовок"""
    raw = (topic_raw or "").strip()
    if raw.startswith("longread-") and "|" in raw:
        return raw.split("|", 1)[1].strip() or None
    return None


def _plain_title(text: str, *, max_len: int = 120, topic_raw: str | None = None) -> str:
    from_topic = _title_from_topic_raw(topic_raw)
    if from_topic:
        if len(from_topic) <= max_len:
            return from_topic
        return from_topic[: max_len - 1].rstrip() + "…"
    plain = re.sub(r"<[^>]+>", "", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_len:
        return plain or "Статья"
    return plain[: max_len - 1].rstrip() + "…"


def _paragraphs_to_html(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "".join(f"<p>{html.escape(p.replace(chr(10), ' '))}</p>" for p in parts)


def _dzen_body_html(title: str, body: str, *, link: str, already_html: bool = False) -> str:
    inner = body if already_html else _paragraphs_to_html(body)
    footer = (
        f'<p><i>Полная версия на сайте '
        f'<a href="{html.escape(link, quote=True)}">neverretire.ru</a>.</i></p>'
    )
    return f"<h2>{html.escape(title)}</h2>\n{inner}\n{footer}"


def _rfc822(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.astimezone(MSK_TZ).strftime("%a, %d %b %Y %H:%M:%S %z")


def _rss_item(
    *,
    title: str,
    link: str,
    guid: str,
    pub_date: datetime,
    description: str,
    content_html: str,
    cover_url: str | None = None,
) -> list[str]:
    desc_plain = _plain_title(description, max_len=300)
    item = [
        "<item>",
        f"<title>{html.escape(title)}</title>",
        f"<link>{html.escape(link, quote=True)}</link>",
        f'<guid isPermaLink="true">{html.escape(guid, quote=True)}</guid>',
        f"<pubDate>{_rfc822(pub_date)}</pubDate>",
        *DZEN_CATEGORIES,
        f"<description>{html.escape(desc_plain)}</description>",
        f"<content:encoded><![CDATA[{content_html}]]></content:encoded>",
    ]
    cover = cover_url or PENSION_DZEN_COVER
    if cover:
        item.append(f'<enclosure url="{html.escape(cover, quote=True)}" type="image/png"/>')
    item.append("</item>")
    return item


def _book_chapter_body(chapter: dict) -> str:
    if chapter.get("body"):
        return chapter["body"]
    sections = chapter.get("sections") or []
    return "\n\n".join(
        f"{s.get('title', '').strip()}\n\n{s.get('body', '').strip()}".strip()
        for s in sections
        if (s.get("body") or "").strip()
    )


def _book_rss_items(limit: int = 6) -> list[list[str]]:
    if not BOOK_JSON.is_file():
        return []
    book = json.loads(BOOK_JSON.read_text(encoding="utf-8"))
    items: list[list[str]] = []
    base_date = datetime.now(MSK_TZ) - timedelta(days=14)
    for i, ch in enumerate(book.get("chapters") or []):
        if len(items) >= limit:
            break
        slug = ch.get("slug") or f"chapter-{i}"
        title = (ch.get("title") or slug).strip()
        subtitle = (ch.get("subtitle") or "").strip()
        full_title = f"{title}. {subtitle}".strip(". ") if subtitle else title
        body = _book_chapter_body(ch)
        if len(body) < 300:
            continue
        link = f"{SITE_BASE}/book/{slug}"
        guid = f"{SITE_BASE}/book/{slug}"
        pub = base_date + timedelta(days=i)
        desc = subtitle or title
        content = _dzen_body_html(full_title, body, link=link, already_html=False)
        items.append(
            _rss_item(
                title=full_title,
                link=link,
                guid=guid,
                pub_date=pub,
                description=desc,
                content_html=content,
            )
        )
    return items


async def _generate_rss_feed(
    *,
    personas: list[str],
    output_path: str,
    channel_title: str,
    channel_description: str,
    author: str,
) -> bool:
    try:
        async with async_session() as session:
            stmt = (
                select(PostDraft)
                .where(
                    PostDraft.status == "published",
                    PostDraft.persona_key.in_(personas),
                )
                .order_by(desc(PostDraft.created_at))
                .limit(RSS_LIMIT)
            )
            posts = list((await session.execute(stmt)).scalars().all())

        now_rfc822 = datetime.now(MSK_TZ).strftime("%a, %d %b %Y %H:%M:%S %z")
        rss_content = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/" '
            'xmlns:atom="http://www.w3.org/2005/Atom" xmlns:georss="http://www.georss.org/georss">',
            "<channel>",
            f"<title>{channel_title}</title>",
            f"<link>{SITE_BASE}</link>",
            f"<description>{channel_description}</description>",
            "<language>ru</language>",
            f"<pubDate>{now_rfc822}</pubDate>",
        ]

        for post in posts:
            pub_date = post.created_at.replace(tzinfo=pytz.utc)
            title = _plain_title(post.text_content or "", topic_raw=post.topic_raw)
            link = _article_link(post)
            body_html = post.text_content or ""
            content = _dzen_body_html(title, body_html, link=link, already_html=True)
            cover = None
            if post.image_path and os.path.exists(post.image_path):
                cover = f"{SITE_BASE}/{post.image_path.lstrip('/')}"
            rss_content.extend(
                _rss_item(
                    title=title,
                    link=link,
                    guid=link,
                    pub_date=pub_date,
                    description=title,
                    content_html=content,
                    cover_url=cover,
                )
            )

        rss_content.extend(["</channel>", "</rss>"])
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(rss_content))
        return True
    except Exception as e:
        print(f"Ошибка при генерации RSS ({output_path}): {e}")
        return False


async def generate_pension_zen_rss() -> bool:
    """RSS для Дзена: статьи + главы книги (≥10 материалов для первой проверки)."""
    try:
        async with async_session() as session:
            stmt = (
                select(PostDraft)
                .where(PostDraft.status == "published", PostDraft.persona_key == "pension")
                .order_by(desc(PostDraft.created_at))
                .limit(RSS_LIMIT)
            )
            posts = list((await session.execute(stmt)).scalars().all())

        book_items = _book_rss_items(limit=8)
        post_items: list[list[str]] = []
        for post in posts:
            title = _plain_title(post.text_content or "", topic_raw=post.topic_raw)
            link = _article_link(post)
            content = _dzen_body_html(
                title, post.text_content or "", link=link, already_html=True
            )
            cover = None
            if post.image_path and os.path.exists(post.image_path):
                cover = f"{SITE_BASE}/{post.image_path.lstrip('/')}"
            post_items.append(
                _rss_item(
                    title=title,
                    link=link,
                    guid=link,
                    pub_date=post.created_at.replace(tzinfo=pytz.utc),
                    description=title,
                    content_html=content,
                    cover_url=cover,
                )
            )

        # Сначала свежие посты, затем книга — всего ≥10 для модерации Дзена
        all_items = post_items + book_items
        if len(all_items) < 10:
            print(f"Предупреждение: в pension RSS только {len(all_items)} материалов (Дзен просит ≥10)")

        now_rfc822 = datetime.now(MSK_TZ).strftime("%a, %d %b %Y %H:%M:%S %z")
        rss_content = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/" '
            'xmlns:atom="http://www.w3.org/2005/Atom" xmlns:georss="http://www.georss.org/georss">',
            "<channel>",
            "<title>На пенсию НИКОГДА</title>",
            f"<link>{SITE_BASE}</link>",
            "<description>Манифест антихрупкости: статьи Иосифа Бороды</description>",
            "<language>ru</language>",
            f"<pubDate>{now_rfc822}</pubDate>",
        ]
        for item in all_items:
            rss_content.extend(item)
        rss_content.extend(["</channel>", "</rss>"])

        os.makedirs(os.path.dirname(PENSION_RSS_PATH) or ".", exist_ok=True)
        with open(PENSION_RSS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(rss_content))
        return True
    except Exception as e:
        print(f"Ошибка pension RSS: {e}")
        return False


async def generate_zen_rss() -> bool:
    """RSS для garden + gdepar (legacy feed)."""
    return await _generate_rss_feed(
        personas=["garden", "gdepar"],
        output_path=RSS_FILE_PATH,
        channel_title="Омни-Медиаимперия: Статьи",
        channel_description="Эксклюзивные статьи от Степаныча и Михалыча",
        author="Empire Authors",
    )


async def generate_all_dzen_rss() -> None:
    await generate_zen_rss()
    await generate_pension_zen_rss()


if __name__ == "__main__":
    import asyncio

    asyncio.run(generate_all_dzen_rss())
