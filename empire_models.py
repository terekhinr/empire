"""Лёгкие ORM-модели для web_app / API без импорта main.py (бот, RAG, embeddings)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///empire.db")
Base = declarative_base()


class PostDraft(Base):
    __tablename__ = "post_drafts"
    id = Column(Integer, primary_key=True)
    persona_key = Column(String)
    text_content = Column(Text)
    image_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime)
