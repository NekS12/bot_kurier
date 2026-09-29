import asyncio
from aiogram import Bot, Dispatcher
from handlers import router as user_router
from admin_handlers import router as admin_router
from database import init_db
from config import BOT_TOKEN
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
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # подключаем роутеры
    dp.include_router(user_router)
    dp.include_router(admin_router)

    asyncio.create_task(background_updater())


    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
