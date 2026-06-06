from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN
from database import (
    init_db,
    add_user,
    set_subscribe,
    add_joke,
    get_random_joke,
    save_rating,
    get_top_jokes,
    set_mood,
    get_mood,
)
from parser import parse_news_keywords, refresh_jokes
from generator import generate_joke, generate_joke_from_news, MOOD_PROMPTS
from scheduler import init_scheduler


def _joke_keyboard(joke_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍", callback_data=f"like_{joke_id}"),
        InlineKeyboardButton("👎", callback_data=f"dislike_{joke_id}"),
    ]])


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "")
    await update.message.reply_text(
        "Привет! Я бот анекдотов 🎭\n\n"
        "/joke — случайный анекдот\n"
        "/refresh — загрузить новые анекдоты с anekdot.ru\n"
        "/generate <тема> — сгенерировать анекдот по теме (ИИ)\n"
        "/generate — анекдот по свежим новостям (ИИ)\n"
        "/mood — выбрать стиль юмора (чёрный, детский, пошлый...)\n"
        "/add <текст> — добавить свой анекдот\n"
        "/top — топ анекдотов\n"
        "/news — свежие заголовки новостей\n"
        "/stop — отписаться от ежедневной рассылки\n"
        "/subscribe — подписаться на рассылку (каждый день в 9:00 МСК)"
    )


async def cmd_joke(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id, update.effective_user.username or "")
    joke = get_random_joke(user_id)
    if not joke:
        await update.message.reply_text("Анекдоты закончились 😢 Попробуй позже.")
        return
    await update.message.reply_text(
        joke["text"],
        reply_markup=_joke_keyboard(joke["joke_id"]),
    )


async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Укажи текст анекдота: /add Текст анекдота")
        return
    add_joke(text, source="user")
    await update.message.reply_text("Анекдот добавлен в базу! 🎉")


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    set_subscribe(update.effective_user.id, False)
    await update.message.reply_text("Ты отписан от ежедневной рассылки. /subscribe — чтобы вернуться.")


async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id, update.effective_user.username or "")
    set_subscribe(update.effective_user.id, True)
    await update.message.reply_text("Ты подписан на ежедневный анекдот в 9:00 МСК 🎉")


async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    jokes = get_top_jokes(10)
    if not jokes:
        await update.message.reply_text("База анекдотов пуста.")
        return
    lines = []
    for i, j in enumerate(jokes, 1):
        preview = j["text"][:100].replace("\n", " ")
        lines.append(f"{i}. [{j['score']:+d}] {preview}…")
    await update.message.reply_text("🏆 Топ анекдотов:\n\n" + "\n\n".join(lines))


async def cmd_mood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    moods = list(MOOD_PROMPTS.keys())
    keyboard = [[InlineKeyboardButton(m, callback_data=f"mood_{m}")] for m in moods]
    current = get_mood(user_id)
    await update.message.reply_text(
        f"Текущее настроение: *{current}*\nВыбери новое:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = get_mood(user_id)
    topic = update.message.text.partition(" ")[2].strip()
    if not topic:
        headlines = parse_news_keywords()
        if not headlines:
            await update.message.reply_text("Не удалось загрузить новости для темы.")
            return
        topic, joke = generate_joke_from_news(headlines, mood)
        joke_id = add_joke(joke, source="ai", theme=topic)
        await update.message.reply_text(f"📰 Тема: {topic}\n\n{joke}", reply_markup=_joke_keyboard(joke_id))
        return

    joke = generate_joke(topic, mood)
    joke_id = add_joke(joke, source="ai", theme=topic)
    await update.message.reply_text(joke, reply_markup=_joke_keyboard(joke_id))


async def cmd_refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Загружаю анекдоты с anekdot.ru...")
    refresh_jokes(add_joke)
    await update.message.reply_text("Готово! Теперь попробуй /joke")


async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keywords = parse_news_keywords()
    if not keywords:
        await update.message.reply_text("Не удалось загрузить новости.")
        return
    text = "📰 Свежие заголовки:\n\n" + "\n".join(f"• {h}" for h in keywords)
    await update.message.reply_text(text)


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("mood_"):
        mood = data.split("_", 1)[1]
        set_mood(user_id, mood)
        await query.edit_message_text(f"Настроение установлено: *{mood}* 🎭", parse_mode="Markdown")
        return

    if data.startswith("like_"):
        joke_id = int(data.split("_", 1)[1])
        save_rating(user_id, joke_id, 1)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Оценено 👍")
    elif data.startswith("dislike_"):
        joke_id = int(data.split("_", 1)[1])
        save_rating(user_id, joke_id, -1)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Оценено 👎")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Укажи BOT_TOKEN в config.py")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("joke", cmd_joke))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("mood", cmd_mood))
    app.add_handler(CallbackQueryHandler(on_callback))

    init_scheduler(app)

    app.run_polling()


if __name__ == "__main__":
    main()
