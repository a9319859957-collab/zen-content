import os, requests
from dotenv import load_dotenv

load_dotenv("/root/indostup-bot/.env")
PROXY = os.getenv("CLOUDFLARE_WORKER_URL").rstrip('/')
KEY = os.getenv("GEMINI_API_KEY")

payload = {"contents": [{"parts": [{"text": "Reply OK"}]}]}
path = f"/v1beta/models/gemini-1.5-flash:generateContent?key={KEY}"

print("=== ГЛУБОКАЯ ДИАГНОСТИКА ПРОКСИ ===")
print(f"Прокси: {PROXY}")

try:
    r1 = requests.post(PROXY, headers={"X-Target-URL": f"https://generativelanguage.googleapis.com{path}"}, json=payload)
    print(f"ТЕСТ 1 (Режим X-Target): Код {r1.status_code} | {r1.text.replace(chr(10), ' ')[:120]}")
except Exception as e: print(f"ТЕСТ 1 Ошибка: {e}")

try:
    r2 = requests.post(PROXY + path, json=payload)
    print(f"ТЕСТ 2 (Прямой путь): Код {r2.status_code} | {r2.text.replace(chr(10), ' ')[:120]}")
except Exception as e: print(f"ТЕСТ 2 Ошибка: {e}")

try:
    r3 = requests.get(PROXY + f"/v1beta/models?key={KEY}")
    print(f"ТЕСТ 3 (Проверка ключа): Код {r3.status_code} | {r3.text.replace(chr(10), ' ')[:120]}")
except Exception as e: print(f"ТЕСТ 3 Ошибка: {e}")
