import sqlite3, os, json, requests, random, time, re, csv
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
        return urls
    except Exception as e:
        print(f"⚠️ Ошибка urls.txt: {e}")
        return ["https://indostup.ru/catalog/"]

def get_keywords_from_csv():
    """Читаем ключи из core.csv"""
    csv_path = os.path.join(BASE_DIR, "core.csv")
    all_keywords = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # Читаем все строки, разбиваем по ; и чистим от пустых значений
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                clean_row = [k.strip() for k in row if k.strip()]
                if clean_row:
                    all_keywords.append(clean_row)
        print(f"📊 Загружено {len(all_keywords)} групп ключевых слов из core.csv")
        return all_keywords
    except Exception as e:
        print(f"⚠️ Ошибка core.csv: {e}")
        return [["доступная среда", "пандусы СПб"]]

def generate_plan(urls, keyword_groups):
    print("🧠 Составляю SEO контент-план на основе семантического ядра...")

    # Выбираем случайные 15 групп ключей для плана
    sample_groups = random.sample(keyword_groups, min(15, len(keyword_groups)))
    
    # Формируем список ключей для промпта
    keywords_str = "\n".join([", ".join(group) for group in sample_groups])

    prompt = (
        f'Ты ведущий SEO-стратег компании "ИнДоступ". '
        f'У тебя есть группы ключевых слов. Для каждой группы придумай ОДНУ тему экспертной статьи для Дзена. '
        f'Статья должна объединять все ключи из своей группы.\n\n'
        f'ГРУППЫ КЛЮЧЕЙ:\n{keywords_str}\n\n'
        f'ЗАДАЧА: Верни JSON-массив объектов. В поле "keywords" запиши все ключи группы через запятую.\n'
        f'ФОРМАТ: [{{"topic": "заголовок", "keywords": "ключ1, ключ2, ключ3"}}]'
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_KEY}"
    headers = {"X-Proxy-Token": PROXY_TOKEN, "X-Target-URL": url, "Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}

    try:
        res = requests.post(PROXY_URL, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            cleaned = text.replace('```json', '').replace('```', '').strip()
            # Добавим обработку на случай если JSON не совсем чистый
            if '[' in cleaned and ']' in cleaned:
                cleaned = cleaned[cleaned.find('['):cleaned.rfind(']')+1]
            return json.loads(cleaned)
        else:
            print(f"⚠️ Ошибка API: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Ошибка генерации плана: {e}")
    return None


def main():
    urls = get_urls()
    keyword_groups = get_keywords_from_csv()
    plan = generate_plan(urls, keyword_groups)
    
    if not plan:
        print("❌ Не удалось получить план.")
        return

    db_path = os.path.join(BASE_DIR, "content_plan.db")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS articles") # Сбросим старый план
        cur.execute("""
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY,
                topic TEXT,
                keyword TEXT, -- Здесь будут храниться все ключи через запятую
                status TEXT,
                target_url TEXT
            )
        """)
        
        for item in plan:
            cur.execute(
                "INSERT INTO articles (topic, keyword, status, target_url) VALUES (?, ?, 'new', ?)",
                (item.get('topic', ''), item.get('keywords', ''), "https://indostup.ru/catalog/")
            )
        conn.commit()

    print(f"✅ План на {len(plan)} тем успешно загружен в базу на основе core.csv.")

if __name__ == "__main__":
    main()
