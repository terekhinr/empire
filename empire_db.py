"""SQLAlchemy models and DB session — без импорта main.py (экономия ~600 MB на worker/gdepar)."""

from __future__ import annotations

import json
import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///empire.db")

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
    topic_raw = Column(Text, nullable=True)
    decision = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    regen_count = Column(Integer, default=0)
    bad_image_count = Column(Integer, default=0)


class TopicHistory(Base):
    __tablename__ = "topic_history"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String, index=True)
    topic_norm = Column(String, index=True)
    topic_raw = Column(Text)
    draft_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BanyaSpot(Base):
    __tablename__ = "banya_spots"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True)
    title = Column(String)
    city = Column(String, index=True)
    region = Column(String, index=True, nullable=True)
    osm_id = Column(String, index=True, nullable=True)
    address = Column(String)
    lat = Column(String)
    lon = Column(String)
    heating = Column(String)
    kind = Column(String)
    site_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    yandex_url = Column(String, nullable=True)
    twogis_url = Column(String, nullable=True)
    cover_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    clips_json = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    visited = Column(Integer, default=0)
    status = Column(String, default="draft", index=True)
    rating_avg = Column(String, nullable=True)
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
    cpa_trial_calls_credited = Column(Integer, default=0)
    cpa_deposit_balance = Column(Integer, default=0)
    phone_blocked = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BanyaCallEvent(Base):
    __tablename__ = "banya_call_events"
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, index=True, nullable=False)
    duration_sec = Column(Integer, nullable=False)
    external_id = Column(String, nullable=True, index=True)
    credited = Column(Integer, default=0)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    __tablename__ = "banya_reviews"
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, index=True)
    source = Column(String, index=True)
    source_id = Column(String, index=True)
    author = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    text = Column(Text)
    url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending", index=True)


async def _alter_post_drafts_schema(conn) -> None:
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
            pass


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=30000"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.run_sync(Base.metadata.create_all)
        await _alter_post_drafts_schema(conn)


async def enqueue_job(job_type: str, payload: dict | None = None) -> int:
    async with async_session() as session:
        job = Job(
            job_type=job_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return int(job.id)
