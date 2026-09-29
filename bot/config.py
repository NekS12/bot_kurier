import os
from dotenv import load_dotenv

load_dotenv()  # загружает .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
DOSTAVKIN_EMAIL = os.getenv("DOSTAVKIN_EMAIL")
DOSTAVKIN_PASSWORD =os.getenv("DOSTAVKIN_PASSWORD")

print("BOT_TOKEN:", BOT_TOKEN)
print("ADMIN_ID_STR:", ADMIN_ID_STR)

DOSTAVKIN_BASE_URL = os.getenv("DOSTAVKIN_BASE_URL", "https://api.dostavkin72.ru")  # уточни точный URL
DOSTAVKIN_API_KEY = os.getenv("DOSTAVKIN_API_KEY")


if BOT_TOKEN is None:
    raise ValueError("Ошибка: не найден BOT_TOKEN в .env")
if ADMIN_ID_STR is None:
    raise ValueError("Ошибка: не найден ADMIN_ID в .env")

ADMIN_ID = int(ADMIN_ID_STR)


from aiogram.utils.token import validate_token
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN", "").strip()
print(f"TOKEN: '{token}'")

validate_token(token)
print("✅ Токен валиден!")
