import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import BOT_TOKEN
from src.db import db
from src.handlers import router
from src.subscriptions_handlers import subscription_router
from src.emplayer_handlers import employer_router

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Asosiy funksiya"""
    # Bot va dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ro'yxatdan o'tkazish
    dp.include_router(router)
    dp.include_router(subscription_router)
    dp.include_router(employer_router)

    try:
        # Ma'lumotlar bazasini ishga tushirish
        await db.create_pool()
        logger.info("✅ Ma'lumotlar bazasi ulanishi o'rnatildi")

        # Botni ishga tushirish
        logger.info("🚀 Bot ishga tushmoqda...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Xatolik yuz berdi: {e}")

    finally:
        # Resurslarni tozalash
        await db.close()
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot qo'lda to'xtatildi")