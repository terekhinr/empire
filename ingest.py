import os
import glob
import logging
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Директории
DATA_DIR = "data"
DB_DIR = "vector_db"

# Каналы (персоны), для которых собираем базы
PERSONAS = ["garden", "gdepar", "lenin", "pension", "stern"]

def get_loader(file_path):
    """Выбирает правильный загрузчик в зависимости от формата файла."""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.pdf':
        return PyPDFLoader(file_path)
    elif ext in ['.txt', '.md']:
        return TextLoader(file_path, encoding='utf-8')
    elif ext == '.docx':
        return Docx2txtLoader(file_path)
    else:
        logger.warning(f"⚠️ Пропуск {file_path}: формат {ext} пока не поддерживается.")
        return None

def main():
    logger.info("🚀 Запуск Архивариуса (Векторизация базы знаний)")
    
    # Инициализация модели для векторизации (работает локально на CPU сервера)
    logger.info("⏳ Загрузка языковой модели для эмбеддингов (это может занять минутку)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # Настройка «ножниц» для текста (режем по 1000 символов с нахлестом 200, чтобы не рвать смысл)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    for persona in PERSONAS:
        persona_data_path = os.path.join(DATA_DIR, persona)
        persona_db_path = os.path.join(DB_DIR, persona)
        
        # Проверяем, есть ли папка с данными для этого канала
        if not os.path.exists(persona_data_path):
            continue
            
        # Собираем все файлы в папке персоны
        files = glob.glob(os.path.join(persona_data_path, "*"))
        if not files:
            logger.info(f"📂 В папке data/{persona} пусто. Пропускаем.")
            continue
            
        logger.info(f"📖 Обработка файлов для канала: [{persona.upper()}]")
        docs = []
        
        for file_path in files:
            loader = get_loader(file_path)
            if loader:
                try:
                    loaded_docs = loader.load()
                    docs.extend(loaded_docs)
                    logger.info(f"  + Загружен файл: {os.path.basename(file_path)} ({len(loaded_docs)} страниц/блоков)")
                except Exception as e:
                    logger.error(f"  ❌ Ошибка чтения {os.path.basename(file_path)}: {e}")
        
        if not docs:
            continue
            
        # Нарезаем документы на чанки
        logger.info(f"  ✂️ Нарезка текста на смысловые фрагменты...")
        chunks = text_splitter.split_documents(docs)
        logger.info(f"  🧩 Получено фрагментов (чанков): {len(chunks)}")
        
        # Создаем векторную базу и сохраняем на диск
        logger.info(f"  🧠 Создание векторного индекса FAISS...")
        db = FAISS.from_documents(chunks, embeddings)
        
        os.makedirs(persona_db_path, exist_ok=True)
        db.save_local(persona_db_path)
        logger.info(f"✅ База для [{persona.upper()}] успешно сохранена в {persona_db_path}\n")

    logger.info("🎉 Работа Архивариуса завершена. Все базы готовы к использованию ИИ.")

if __name__ == "__main__":
    main()