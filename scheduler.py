from apscheduler.schedulers.background import BackgroundScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DAILY_HOUR, DAILY_MINUTE, TIMEZONE
from database import get_subscribed_users, get_random_joke
import asyncio


def _joke_keyboard(joke_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍", callback_data=f"like_{joke_id}"),
        InlineKeyboardButton("👎", callback_data=f"dislike_{joke_id}"),
    ]])


async def _broadcast(bot):
    for user_id in get_subscribed_users():
        joke = get_random_joke(user_id)
        if joke:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=joke["text"],
                    reply_markup=_joke_keyboard(joke["joke_id"]),
                )
            except Exception:
                pass


def _run_broadcast(bot):
    asyncio.run(_broadcast(bot))


def init_scheduler(bot_app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_broadcast,
        "cron",
        args=[bot_app.bot],
        hour=DAILY_HOUR,
        minute=DAILY_MINUTE,
        timezone=TIMEZONE,
    )
    scheduler.start()
    return scheduler
