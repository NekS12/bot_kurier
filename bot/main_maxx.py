import asyncio

from aiomax import Bot
from aiomax.router import Router
from handlers import router as user_router
from admin_handlers import router as admin_router
from database import init_db
from config_maxx import BOT_TOKENM
from api_dostavkin import update_orders


async def background_updater():
    """Фоновая задача, обновляющая заказы каждые 2 минуты"""
    while True:
        try:
            await update_orders()  # обновляем заказы
            print("♻️ Обновление заказов завершено.")
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении заказов: {e}")
        await asyncio.sleep(120)  # ждём 2 минуты


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKENM)

    # Создаём главный роутер и подключаем вложенные роутеры
    root_router = Router()
    root_router.add_router(user_router)
    root_router.add_router(admin_router)

    # Запускаем фоновую задачу
    asyncio.create_task(background_updater())

    # Старт бота с подключённым роутером
    await bot.start(router=root_router)


if __name__ == "__main__":
    asyncio.run(main())
