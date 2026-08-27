import os
import json
import pypdf as PyPDF2
import re

QUEUE_FILE = "data/lenin_books_queue.json"

FILES = {
    "Стихи": "Стихи о Ленине (Школьная библиотека) — 1974.pdf",
    "Сказки": "Замостьянов А.А. (сост.) - Сказки о Ленине (Родительское собрание) - 2023.pdf",
    "Рассказы": "Кононов А.Т. - Рассказы о Ленине - 1974.pdf"
}

def clean_text(text):
    # Убираем разрывы строк, номера страниц и лишние пробелы
    text = re.sub(r'--- PAGE \d+ ---', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def chunk_text(text, source_type, chunk_size=1500):
    chunks = []
    # Бьем текст по точкам, чтобы не обрывать предложения
    sentences = text.split('. ')
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append({"source": source_type, "text": current_chunk.strip()})
            current_chunk = sentence + ". "
            
    if current_chunk:
        chunks.append({"source": source_type, "text": current_chunk.strip()})
    return chunks

def process_books():
    os.makedirs("data", exist_ok=True)
    all_chunks = {"Стихи": [], "Сказки": [], "Рассказы": []}
    
    for category, filename in FILES.items():
        if not os.path.exists(filename):
            print(f"⚠️ Файл {filename} не найден. Пропускаю.")
            continue
            
        print(f"📖 Обработка: {filename}...")
        raw_text = ""
        try:
            with open(filename, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    raw_text += page.extract_text() + " "
        except Exception as e:
            print(f"Ошибка чтения {filename}: {e}")
            
        cleaned = clean_text(raw_text)
        all_chunks[category] = chunk_text(cleaned, category)

    # Перемешиваем по очереди: Стих -> Сказка -> Рассказ -> Стих...
    interleaved_queue = []
    max_len = max(len(all_chunks["Стихи"]), len(all_chunks["Сказки"]), len(all_chunks["Рассказы"]))
    
    for i in range(max_len):
        if i < len(all_chunks["Стихи"]): interleaved_queue.append(all_chunks["Стихи"][i])
        if i < len(all_chunks["Сказки"]): interleaved_queue.append(all_chunks["Сказки"][i])
        if i < len(all_chunks["Рассказы"]): interleaved_queue.append(all_chunks["Рассказы"][i])
        
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(interleaved_queue, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Готово! Нарезано {len(interleaved_queue)} фрагментов и сохранено в {QUEUE_FILE}.")

if __name__ == "__main__":
    process_books()