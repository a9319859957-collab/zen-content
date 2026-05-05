#!/usr/bin/env python3
"""
Одноразовый скрипт:
1. Генерирует HTML-страницу для каждой статьи из RSS
2. Чинит <link> и <guid> в существующем rss.xml
3. Добавляет <language> и <atom:link> в <channel>
"""
import os, re
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SITE_URL = os.getenv("GITHUB_PAGES_URL", "https://your-link.github.io")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
RSS_PATH = os.path.join(OUTPUT_DIR, "rss.xml")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{main_img_url}">
<meta property="og:type" content="article">
<style>body{{max-width:800px;margin:0 auto;padding:20px;font-family:sans-serif;line-height:1.6}}img{{max-width:100%}}</style>
</head>
<body>
<article>
{content}
</article>
</body>
</html>"""


def parse_articles_from_rss(rss_text):
    """Извлекаем данные статей из RSS без ElementTree (обходим CDATA)"""
    items = re.findall(r'<item>(.*?)</item>', rss_text, re.DOTALL)
    articles = []
    for item in items:
        title = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
        link = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
        guid = re.search(r'<guid[^>]*>(.*?)</guid>', item, re.DOTALL)
        desc = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL)
        content = re.search(r'<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>', item, re.DOTALL)
        enclosure = re.search(r'<enclosure url="([^"]+)"', item)

        slug = guid.group(1).strip() if guid else ''
        # Если guid выглядит как URL — берём последний сегмент пути
        if slug.startswith('http'):
            slug = slug.rstrip('/').split('/')[-1]
            if slug.endswith('.html'):
                slug = slug[:-5]

        articles.append({
            'title': title.group(1).strip() if title else '',
            'old_link': link.group(1).strip() if link else '',
            'slug': slug,
            'description': desc.group(1).strip() if desc else '',
            'content': content.group(1).strip() if content else '',
            'main_img': enclosure.group(1).strip() if enclosure else '',
        })
    return articles


def generate_html(article):
    slug = article['slug']
    if not slug:
        return
    html_path = os.path.join(OUTPUT_DIR, f"{slug}.html")
    article_url = f"{SITE_URL}/output/{slug}.html"
    main_img_url = article['main_img']

    # Заменяем ссылки на картинки внутри content (они уже раскрыты — IMG_1# заменён ранее)
    content = article['content']

    html = HTML_TEMPLATE.format(
        title=article['title'],
        description=article['description'],
        main_img_url=main_img_url,
        content=content,
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ {slug}.html")
    return article_url


def fix_rss(rss_text, articles):
    """Правим RSS построчно — меняем link, guid, добавляем channel-теги"""

    # 1. Для каждой статьи правим <link> и <guid>
    for art in articles:
        slug = art['slug']
        old_link = art['old_link']
        new_link = f"{SITE_URL}/output/{slug}.html"

        if old_link != new_link:
            rss_text = rss_text.replace(
                f"<link>{old_link}</link>",
                f"<link>{new_link}</link>",
                1
            )
            print(f"  🔗 link исправлен: {slug}")

        # Заменяем <guid>slug</guid> → <guid isPermaLink="true">url</guid>
        rss_text = re.sub(
            rf'<guid[^>]*>{re.escape(slug)}</guid>',
            f'<guid isPermaLink="true">{new_link}</guid>',
            rss_text,
            count=1
        )

    # 2. Добавляем xmlns:atom в корневой тег если нет
    if 'xmlns:atom' not in rss_text:
        rss_text = rss_text.replace(
            'xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0"',
            'xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom" version="2.0"'
        )

    # 3. Добавляем <language> если нет
    if '<language>' not in rss_text:
        rss_text = rss_text.replace(
            '<description>Блог экспертов по адаптации зданий для МГН</description>',
            '<description>Блог экспертов по адаптации зданий для МГН</description>\n    <language>ru</language>'
        )

    # 4. Добавляем <atom:link rel="self"> если нет
    rss_url = f"{SITE_URL}/output/rss.xml"
    if 'atom:link' not in rss_text:
        rss_text = rss_text.replace(
            f'<link>{SITE_URL}</link>',
            f'<link>{SITE_URL}</link>\n    <atom:link href="{rss_url}" rel="self" type="application/rss+xml"/>'
        )

    return rss_text


def main():
    print(f"SITE_URL = {SITE_URL}\n")

    with open(RSS_PATH, "r", encoding="utf-8") as f:
        rss_text = f.read()

    articles = parse_articles_from_rss(rss_text)
    print(f"Найдено статей: {len(articles)}\n")

    print("Генерирую HTML-страницы:")
    for art in articles:
        generate_html(art)

    print("\nПравлю RSS:")
    fixed = fix_rss(rss_text, articles)

    with open(RSS_PATH, "w", encoding="utf-8") as f:
        f.write(fixed)
    print("\n✅ RSS обновлён.")


if __name__ == "__main__":
    main()
