import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import Config
from bot.db.database import init_db, close_db
from bot.handlers.user import user_router
from bot.handlers.admin import admin_router
from bot.middlewares.admin import AdminMiddleware
from bot.services.subscription_checker import check_subscriptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

config = Config()
scheduler = AsyncIOScheduler()


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return

    if not config.ADMIN_IDS:
        logger.warning("ADMIN_IDS is not set - admin commands will be unavailable.")

    logger.info("Initializing database...")
    await init_db(config.async_database_url)

    logger.info("Starting bot...")
    bot = Bot(token=config.BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(user_router)

    if config.ADMIN_IDS:
        admin_mw = AdminMiddleware(config.ADMIN_IDS)
        admin_router.message.middleware(admin_mw)
        admin_router.callback_query.middleware(admin_mw)
        dp.include_router(admin_router)

    scheduler.add_job(
        check_subscriptions,
        IntervalTrigger(hours=1),
        args=[bot, config.ADMIN_IDS],
        id="subscription_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Subscription checker scheduled (every 60 minutes).")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
