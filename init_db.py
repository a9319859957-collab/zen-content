#!/usr/bin/env python3
import sqlite3
import os
import json
import requests
from dotenv import load_dotenv

# Динамический путь для Mac
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PROXY_URL = os.getenv("CLOUDFLARE_WORKER_URL")
PROXY_TOKEN = os.getenv("CLOUDFLARE_PROXY_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = os.path.join(BASE_DIR, "content_plan.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            target_audience TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            published_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            keyword TEXT,
            target_url TEXT
        )
    ''')
    conn.commit()
    return conn

def generate_content_plan(conn):
    print("🤖 Прошу Gemini сгенерировать контент-план...")
    prompt = """
    Ты — SEO-стратег компании "ИнДоступ" (indostup.ru).
    Наша ЦА: B2B и B2G (застройщики, директора школ, поликлиник, музеев, подрядчики по 44-ФЗ/223-ФЗ).
    Составь контент-план из 12 экспертных тем. Темы должны касаться ГОСТов, СНиПов (СП 59.13330.2020), проверок, закрытия раздела МГН, зон безопасности и санузлов.
    Верни СТРОГО валидный JSON в формате:
    [
      {"topic": "Название темы", "target_audience": "Кто читает"}
    ]
    Никакого текста кроме JSON.
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"X-Proxy-Token": PROXY_TOKEN, "X-Target-URL": url, "Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}

    response = requests.post(PROXY_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"❌ Ошибка API: {response.status_code}")
        return

    try:
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        raw_text = raw_text.replace('```json', '').replace('```', '').strip()
        topics = json.loads(raw_text)
        
        cursor = conn.cursor()
        for item in topics:
            cursor.execute("INSERT INTO articles (topic, target_audience, status) VALUES (?, ?, 'new')", 
                           (item['topic'], item['target_audience']))
        conn.commit()
        print(f"✅ Успешно добавлено {len(topics)} тем в базу!")
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")

if __name__ == "__main__":
    db_conn = init_db()
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    if cur.fetchone()[0] == 0:
        generate_content_plan(db_conn)
    else:
        print("ℹ️ В базе уже есть темы. Генерация пропущена.")
