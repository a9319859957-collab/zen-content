import sqlite3, os, json, requests, random, time, re
from dotenv import load_dotenv

# Динамический путь для Mac
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PROXY_URL = os.getenv("CLOUDFLARE_WORKER_URL")
PROXY_TOKEN = os.getenv("CLOUDFLARE_PROXY_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")


def get_urls():
    """Читаем список URL каталога из файла"""
    urls_path = os.path.join(BASE_DIR, "urls.txt")
    try:
        with open(urls_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        print(f"📋 Загружено {len(urls)} URL каталога")
        return urls
    except Exception as e:
        print(f"⚠️ Не удалось прочитать urls.txt: {e}")
        return ["https://indostup.ru/catalog/"]


def generate_plan(urls):
    print("🧠 Составляю контент-план (Модель: Gemini 3 Flash Preview)...")

    keywords = [
        "доступная среда", "пандусы СПб", "тактильная плитка",
        "ГАСН проверка", "СП 59.13330", "адаптация зданий"
    ]

    sample_urls = random.sample(urls, min(20, len(urls)))

    prompt = (
        f'Ты SEO-эксперт компании "ИнДоступ" (Санкт-Петербург). '
        f'Составь контент-план из 14 экспертных тем для блога. '
        f'ЦЕЛЕВАЯ АУДИТОРИЯ: Застройщики, генподрядчики, госучреждения. '
        f'КЛЮЧЕВЫЕ СЛОВА: {", ".join(keywords)}.\n\n'
        f'СТРАНИЦЫ КАТАЛОГА САЙТА (для внутренних ссылок):\n'
        f'{chr(10).join(sample_urls)}\n\n'
        f'ЗАДАЧА: Для каждой темы подбери наиболее релевантный URL из списка выше '
        f'для внутренней ссылки в статье. Ссылка должна точно соответствовать теме.\n\n'
        f'ФОРМАТ: Верни СТРОГО JSON-массив объектов:\n'
        f'[{{"topic": "тема статьи", "keyword": "ключевое слово", "target_url": "https://indostup.ru/catalog/..."}}]'
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"
    headers = {
        "X-Proxy-Token": PROXY_TOKEN,
        "X-Target-URL": url,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7},
    }

    for attempt in range(1, 4):
        try:
            res = requests.post(PROXY_URL, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                text = res.json()['candidates'][0]['content']['parts'][0]['text']
                try:
                    cleaned = text.replace('```json', '').replace('```', '').strip()
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                    print(f"⚠️ Попытка {attempt}: ответ не содержит валидного JSON")
            else:
                print(f"⚠️ Попытка {attempt}: Ошибка {res.status_code} | {res.text[:200]}")
            time.sleep(10)
        except Exception as e:
            print(f"❌ Ошибка (попытка {attempt}): {e}")
            time.sleep(5)
    return None


def main():
    urls = get_urls()
    plan = generate_plan(urls)
    if not plan:
        print("❌ Не удалось получить план.")
        return

    db_path = os.path.join(BASE_DIR, "content_plan.db")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                topic TEXT,
                keyword TEXT,
                status TEXT,
                target_url TEXT
            )
        """)
        cur.execute("DELETE FROM articles WHERE status='new'")
        for item in plan:
            target = item.get('target_url', '')
            if not target.startswith('https://indostup.ru/catalog/'):
                target = 'https://indostup.ru/catalog/'
            cur.execute(
                "INSERT INTO articles (topic, keyword, status, target_url) VALUES (?, ?, 'new', ?)",
                (item.get('topic', ''), item.get('keyword', ''), target)
            )
        conn.commit()

    print(f"✅ План на {len(plan)} тем успешно загружен в базу.")
    print("📎 Проверка target_url:")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT topic, target_url FROM articles WHERE status='new'")
        for row in cur.fetchall():
            print(f"   {row[0][:50]} → {row[1]}")


if __name__ == "__main__":
    main()
