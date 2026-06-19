import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WIKI_API_URL = "https://commons.wikimedia.org/w/api.php"
BASE_DIR = "media/lenin"

def download_lenin_by_years():
    headers = {"User-Agent": "EmpireBot/2.0 (neverretire.ru; terekhin.r@gmail.com)"}
    
    # Годы активной деятельности Ленина
    for year in range(1895, 1925):
        category = f"Category:Vladimir_Lenin_in_{year}"
        year_dir = os.path.join(BASE_DIR, str(year))
        
        params = {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": category,
            "gcmtype": "file",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
            "gcmlimit": 20 # Берем до 20 фото на каждый год
        }
        
        try:
            res = requests.get(WIKI_API_URL, headers=headers, params=params, timeout=15)
            data = res.json()
            pages = data.get("query", {}).get("pages", {})
            
            if not pages:
                continue # В этом году нет фото в этой категории
                
            os.makedirs(year_dir, exist_ok=True)
            count = 0
            
            for page_id, info in pages.items():
                img_url = info.get("imageinfo", [{}])[0].get("url")
                if img_url and img_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(year_dir, f"lenin_{year}_{count}.jpg")
                    img_data = requests.get(img_url, headers=headers, timeout=10).content
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    count += 1
            if count > 0:
                logger.info(f"✅ Год {year}: скачано {count} фото.")
        except Exception as e:
            logger.error(f"❌ Ошибка для {year}: {e}")

if __name__ == "__main__":
    download_lenin_by_years()