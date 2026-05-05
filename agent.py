import sqlite3, os, json, requests, time, urllib.parse, random, re, base64, subprocess
from dotenv import load_dotenv
from datetime import datetime

# Динамический путь для Mac
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PROXY_URL = os.getenv("CLOUDFLARE_WORKER_URL")
PROXY_TOKEN = os.getenv("CLOUDFLARE_PROXY_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SITE_URL = os.getenv("GITHUB_PAGES_URL", "https://your-link.github.io")

CURRENT_YEAR = datetime.now().year
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")

# Создаем папки если нет
os.makedirs(MEDIA_DIR, exist_ok=True)

def git_push():
    """Автоматическая отправка изменений на GitHub"""
    try:
        print("📤 Отправляю изменения на GitHub...")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-publish: {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
        # Если вы уже настроили remote origin, эта команда сработает
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            print("🚀 Успешно загружено на GitHub!")
        else:
            print(f"⚠️ Ошибка push (возможно, не настроен remote): {result.stderr}")
    except Exception as e:
        print(f"❌ Ошибка Git: {e}")

def save_image(b64_data, filename):
    """Сохранение base64 в файл"""
    if not b64_data:
        return None
    try:
        path = os.path.join(MEDIA_DIR, filename)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return filename
    except Exception as e:
        print(f"❌ Ошибка сохранения фото: {e}")
        return None

def get_photo_b64(image_prompt):
    """Генерация фото через Gemini 3.1 Flash Image Preview"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={GEMINI_KEY}"
    headers = {
        "X-Proxy-Token": PROXY_TOKEN,
        "X-Target-URL": url,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": image_prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }

    for attempt in range(1, 4):
        try:
            res = requests.post(PROXY_URL, headers=headers, json=payload, timeout=120)
            if res.status_code == 200:
                parts = res.json()['candidates'][0]['content']['parts']
                for part in parts:
                    if 'inlineData' in part:
                        data = part['inlineData']['data']
                        print(f"📸 Картинка сгенерирована ({len(data) // 1024} KB)")
                        return data
            elif res.status_code == 503:
                time.sleep(30)
            else:
                time.sleep(10)
        except Exception as e:
            time.sleep(10)
    return None

def get_article(topic, keyword, target_url):
    """Написание статьи через Gemini"""
    print(f"✍️ Пишу статью для Дзена: '{topic}'...")

    prompt = f"""Пиши экспертную статью для Яндекс.Дзена от лица компании «Индоступ» (Санкт-Петербург).
ТЕМА: '{topic}' | КЛЮЧ: '{keyword}'
Упомяни 1 раз ссылку на наш сайт: <a href="{target_url}">[естественный анкорный текст]</a>.

ТРЕБОВАНИЯ:
1. СТИЛЬ: Живой, интересный, для людей. Используй подзаголовки, списки.
2. СТРУКТУРА: H1 -> Вступление -> Разделы H2 -> Список советов -> Заключение.
3. ОФОРМЛЕНИЕ: Только HTML (h2, p, ul, li, strong).
4. КАРТИНКА: Вставь маркер #IMG_1# в середине.

Верни СТРОГО JSON:
{{
  "title": "Заголовок для Дзена",
  "description": "Краткий анонс для RSS",
  "content": "HTML-код статьи",
  "slug": "translit-slug",
  "image_prompts": {{
    "main": "English prompt for main cover photo, realistic, 16:9",
    "main_alt": "Alt текст для главной",
    "inner": "English prompt for in-text photo, construction details",
    "inner_alt": "Alt текст для внутренней"
  }}
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key={GEMINI_KEY}"
    headers = {"X-Proxy-Token": PROXY_TOKEN, "X-Target-URL": url, "Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8}}

    try:
        res = requests.post(PROXY_URL, headers=headers, json=payload, timeout=90)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            cleaned = text.replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned)
    except Exception as e:
        print(f"❌ Ошибка генерации текста: {e}")
    return None

def update_rss(article_data):
    """Добавление статьи в локальный RSS-файл"""
    rss_path = os.path.join(OUTPUT_DIR, "rss.xml")
    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0300")
    
    item = f"""
    <item>
        <title>{article_data['title']}</title>
        <link>{SITE_URL}/output/media/{article_data['main_img']}</link>
        <guid>{article_data['slug']}</guid>
        <pubDate>{now}</pubDate>
        <description><![CDATA[{article_data['description']}]]></description>
        <content:encoded><![CDATA[
            {article_data['content'].replace('#IMG_1#', f'<img src="{SITE_URL}/output/media/{article_data["inner_img"]}"/>')}
        ]]></content:encoded>
        <enclosure url="{SITE_URL}/output/media/{article_data['main_img']}" type="image/jpeg"/>
    </item>"""
    
    if not os.path.exists(rss_path):
        header = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <title>Индоступ - Доступная среда</title>
    <link>{SITE_URL}</link>
    <description>Блог экспертов по адаптации зданий для МГН</description>
    <!-- ITEMS_HERE -->
  </channel>
</rss>"""
        with open(rss_path, "w", encoding="utf-8") as f:
            f.write(header)

    with open(rss_path, "r+", encoding="utf-8") as f:
        content = f.read()
        new_content = content.replace("<!-- ITEMS_HERE -->", item + "\n    <!-- ITEMS_HERE -->")
        f.seek(0)
        f.write(new_content)
    
    print(f"✅ Статья добавлена в RSS: {rss_path}")

def main():
    db_path = os.path.join(BASE_DIR, "content_plan.db")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, topic, keyword, target_url FROM articles WHERE status='new' LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("✅ Все темы опубликованы.")
            return

        article_id, topic, keyword, target_url = row
        data = get_article(topic, keyword, target_url)
        if not data: return

        # Генерация и сохранение картинок
        print("🖼️ Генерирую обложку...")
        main_b64 = get_photo_b64(data['image_prompts']['main'])
        main_img_name = f"{data['slug']}_main.jpg"
        save_image(main_b64, main_img_name)

        print("🖼️ Генерирую картинку в текст...")
        inner_b64 = get_photo_b64(data['image_prompts']['inner'])
        inner_img_name = f"{data['slug']}_inner.jpg"
        save_image(inner_b64, inner_img_name)

        # Публикация в RSS
        data['main_img'] = main_img_name
        data['inner_img'] = inner_img_name
        
        update_rss(data)
        
        cur.execute("UPDATE articles SET status='published' WHERE id=?", (article_id,))
        conn.commit()

        # Автоматическая отправка на GitHub
        git_push()

if __name__ == "__main__":
    main()
