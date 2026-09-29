import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Основные настройки
BOT_TOKENM= os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
DOSTAVKIN_EMAIL = os.getenv("DOSTAVKIN_EMAIL")
DOSTAVKIN_PASSWORD = os.getenv("DOSTAVKIN_PASSWORD")
DOSTAVKIN_BASE_URL = os.getenv("DOSTAVKIN_BASE_URL", "https://api.dostavkin72.ru")
DOSTAVKIN_API_KEY = os.getenv("DOSTAVKIN_API_KEY")

# Проверка обязательных переменных
if not BOT_TOKENM:
    raise ValueError("Ошибка: не найден BOT_TOKEN в .env")
if not ADMIN_ID_STR:
    raise ValueError("Ошибка: не найден ADMIN_ID в .env")

# Преобразуем ADMIN_ID в int
ADMIN_ID = int(ADMIN_ID_STR)

# Валидация токена для aiomax
token = BOT_TOKEN.strip()
print("✅ Токен валиден!")

# Для отладки
print("BOT_TOKEN:", BOT_TOKEN)
print("ADMIN_ID:", ADMIN_ID)
print("DOSTAVKIN_EMAIL:", DOSTAVKIN_EMAIL)
