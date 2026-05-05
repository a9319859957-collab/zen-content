import os, requests
from dotenv import load_dotenv

load_dotenv("/root/indostup-bot/.env")
PROXY_URL = os.getenv("CLOUDFLARE_WORKER_URL")
PROXY_TOKEN = os.getenv("CLOUDFLARE_PROXY_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
headers = {"X-Proxy-Token": PROXY_TOKEN, "X-Target-URL": url, "Content-Type": "application/json"}
payload = {"contents": [{"parts": [{"text": "Напиши слово 'Успех', если слышишь меня."}]}]}

print(f"📡 Стучимся в прокси: {PROXY_URL}")
res = requests.post(PROXY_URL, headers=headers, json=payload)
print(f"\n--- СЫРОЙ ОТВЕТ СЕРВЕРА (Код {res.status_code}) ---")
print(res.text)
print("-------------------------------------------------")
