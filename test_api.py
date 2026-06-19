import httpx
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

async def check():
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        # 1. Проверяем баланс и доступность
        print("🔍 Проверка ключа...")
        res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
        print(f"Статус ключа: {res.status_code}")
        print(f"Ответ: {res.text}\n")

        # 2. Получаем список РЕАЛЬНО доступных тебе моделей
        print("🔍 Список доступных моделей...")
        res_models = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        if res_models.status_code == 200:
            models = res_models.json().get('data', [])
            # Ищем любые модели Google или Anthropic
            available = [m['id'] for m in models if 'google' in m['id'] or 'anthropic' in m['id']]
            print(f"Найдено моделей: {len(available)}")
            print(f"Первые 5: {available[:5]}")
        else:
            print(f"Ошибка получения моделей: {res_models.status_code}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check())