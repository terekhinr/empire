import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVE_DIR = "media/lenin/archive"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# API Wikimedia Commons
WIKI_API_URL = "https://commons.wikimedia.org/w/api.php"

def download_lenin_photos(limit=100):
    logger.info("🕵️‍♂️ Запуск парсера: глобальный поиск исторических фото В.И. Ленина...")
    
    headers = {
        "User-Agent": "EmpireBot/1.2 (neverretire.ru; terekhin.r@gmail.com)"
    }
    
    # Меняем метод с 'categorymembers' на 'search' (глобальный поиск)
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": "Vladimir Lenin historical photograph",
        "gsrnamespace": 6, # Пространство имен 6 означает "Файлы"
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }

    try:
        response = requests.get(WIKI_API_URL, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"❌ Сервер отклонил запрос (Код: {response.status_code})")
            return
            
        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        if not pages:
            logger.warning("⚠️ Поиск не дал результатов. Попробуйте изменить поисковый запрос.")
            return

        count = 0
        for page_id, page_info in pages.items():
            image_info = page_info.get("imageinfo")
            if not image_info:
                continue
                
            img_url = image_info[0].get("url")
            
            # Фильтруем: берем только JPG, JPEG, PNG
            if img_url and img_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_name = f"lenin_archive_{count}.jpg"
                img_path = os.path.join(ARCHIVE_DIR, img_name)
                
                try:
                    # Скачиваем саму картинку
                    img_data = requests.get(img_url, headers=headers, timeout=15).content
                    with open(img_path, "wb") as handler:
                        handler.write(img_data)
                    
                    logger.info(f"✅ Скачано фото: {img_name}")
                    count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Пропуск файла (ошибка скачивания {img_url}): {e}")

        logger.info(f"🎉 Готово! Сохранено {count} реальных фотографий Ленина в {ARCHIVE_DIR}")

    except Exception as e:
        logger.error(f"❌ Ошибка парсинга Wikimedia: {e}")

if __name__ == "__main__":
    download_lenin_photos(100)