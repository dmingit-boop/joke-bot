import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "jokes.db")
DAILY_HOUR = int(os.environ.get("DAILY_HOUR", 9))
DAILY_MINUTE = int(os.environ.get("DAILY_MINUTE", 0))
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Moscow")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
