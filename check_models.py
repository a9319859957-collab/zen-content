import os, requests
from dotenv import load_dotenv

load_dotenv("/root/indostup-bot/.env")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PROXY_URL = os.getenv("CLOUDFLARE_WORKER_URL")
PROXY_TOKEN = os.getenv("CLOUDFLARE_PROXY_TOKEN")

# Запрашиваем список всех моделей у Google
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
headers = {"X-Proxy-Token": PROXY_TOKEN, "X-Target-URL": url}

print("🔎 Стучусь в Google API, чтобы получить список твоих моделей...")

try:
    # Делаем GET-запрос через твой прокси
    r = requests.get(PROXY_URL, headers=headers, timeout=30)
    
    if r.status_code == 200:
        models = r.json().get('models', [])
        print("\n✅ СПИСОК ДОСТУПНЫХ МОДЕЛЕЙ (для генерации текста):")
        print("-" * 50)
        for m in models:
            # Фильтруем только те, которые умеют писать текст (generateContent)
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                # Отрезаем приставку 'models/', чтобы получить чистое имя
                clean_name = m['name'].replace('models/', '')
                print(f"🔸 {clean_name}")
        print("-" * 50)
    else:
        print(f"⚠️ Ошибка ответа: Код {r.status_code} | {r.text}")
except Exception as e:
     print(f"❌ Ошибка соединения: {e}")
