import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, select

# Считываем URL базы из переменной окружения (которую мы пропишем в docker-compose)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/stepanich_db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- ТАБЛИЦА БАЗЫ ЗНАНИЙ (ПСС, ГОСТы, Методички) ---
class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    persona: Mapped[str] = mapped_column(String(50))  # garden, lenin, stern, gdepar
    source_name: Mapped[str] = mapped_column(String(255)) # Источник: "ПСС Том 1", "Инструкция к печи"
    content: Mapped[str] = mapped_column(Text)  # Сам текст факта
    tags: Mapped[str] = mapped_column(String(255), nullable=True) # "рассада", "буржуазия"

# --- ФУНКЦИЯ ДЛЯ ПОИСКА ЗНАНИЙ ---
async def get_knowledge(persona: str, query: str = None):
    async with async_session() as session:
        # Пока упрощенный поиск: берем всё по конкретной персоне
        # В будущем добавим полнотекстовый поиск по query
        stmt = select(KnowledgeBase).where(KnowledgeBase.persona == persona).limit(5)
        result = await session.execute(stmt)
        return result.scalars().all()

# Инициализация таблиц (создаст их, если нет)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)