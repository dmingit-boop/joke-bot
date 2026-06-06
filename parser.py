import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JokeBot/1.0)"}


def parse_jokes_from_anekdot_ru() -> list:
    try:
        resp = requests.get(
            "https://www.anekdot.ru/random/anekdot/",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jokes = [tag.get_text(strip=True) for tag in soup.select("div.text")]
        return [j for j in jokes if j]
    except Exception:
        return []


BORING_WORDS = [
    "заседани", "совещани", "встреч", "переговор", "подписа", "утвержд",
    "заявил", "сообщил", "рассказал", "отметил", "призвал", "предложил",
    "бюджет", "налог", "тариф", "индекс", "ставк", "процент",
]

INTERESTING_SOURCES = [
    "https://lenta.ru/rss/news",
    "https://lenta.ru/rss/articles",
    "https://www.rbc.ru/rss/news",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",
    "https://www.kommersant.ru/RSS/main.xml",
    "https://iz.rz/xml/rss/all.xml",
]


def _is_boring(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in BORING_WORDS)


def parse_news_keywords() -> list:
    all_titles = []
    for url in INTERESTING_SOURCES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            titles = [
                item.findtext("title", "").strip()
                for item in root.iter("item")
            ]
            all_titles.extend([t for t in titles if t])
        except Exception:
            continue

    if not all_titles:
        return []

    interesting = [t for t in all_titles if not _is_boring(t)]
    pool = interesting if interesting else all_titles

    import random
    random.shuffle(pool)
    return pool[:15]


def refresh_jokes(db_add_func):
    jokes = parse_jokes_from_anekdot_ru()
    for text in jokes:
        db_add_func(text, source="anekdot.ru")
