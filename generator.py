import requests
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

API_URL = "https://openrouter.ai/api/v1/chat/completions"


MOOD_PROMPTS = {
    "чёрный": "Используй чёрный юмор, мрачные шутки, можно цинично.",
    "детский": "Анекдот должен быть добрым, безобидным, подходящим для детей.",
    "пошлый": "Можно пошлые намёки и взрослый юмор 18+.",
    "абсурдный": "Анекдот должен быть абсурдным и сюрреалистичным.",
    "политический": "Тема политики, чиновников, власти.",
    "обычный": "Обычный смешной анекдот.",
}


def generate_joke(topic: str, mood: str = "обычный") -> str:
    mood_hint = MOOD_PROMPTS.get(mood, MOOD_PROMPTS["обычный"])
    prompt = (
        f"Придумай короткий смешной анекдот на тему: «{topic}». "
        f"{mood_hint} "
        "Только текст анекдота, без предисловий и пояснений."
    )
    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Не удалось сгенерировать анекдот: {e}"


def pick_weirdest_headline(headlines: list) -> str:
    numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
    prompt = (
        f"Вот список новостных заголовков:\n{numbered}\n\n"
        "Выбери ОДИН самый необычный, странный или смешной заголовок. "
        "Ответь ТОЛЬКО номером, без пояснений."
    )
    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        idx = int("".join(filter(str.isdigit, answer))) - 1
        if 0 <= idx < len(headlines):
            return headlines[idx]
    except Exception:
        pass
    import random
    return random.choice(headlines)


def generate_joke_from_news(news_headlines: list, mood: str = "обычный") -> tuple:
    if not news_headlines:
        return None, None
    topic = pick_weirdest_headline(news_headlines)
    joke = generate_joke(topic, mood)
    return topic, joke
