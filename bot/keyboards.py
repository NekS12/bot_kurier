from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# кнопка для отправки номера
request_phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
    ],
    resize_keyboard=True
)

# админ-панель
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Список пользователей")],
        [KeyboardButton(text="📍 Курьеры на карте")],
        [KeyboardButton(text="🔍 Поиск по ID")],
        [KeyboardButton(text="🚪 Выйти")]
    ],
    resize_keyboard=True
)

# меню для обычных пользователей
'''user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Работа с заказами")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📍 Отправить геопозицию", request_location=True)]
    ],
    resize_keyboard=True
)'''



courier_orders_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Мои заказы"), KeyboardButton(text="🔓 Открытые заказы")],
        [KeyboardButton(text="🆘 Помощь"), KeyboardButton(text="💬 Обратная связь")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🔙 Назад в меню")]
    ],
    resize_keyboard=True
)

status_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Открыть смену")]
    ],
    resize_keyboard=True
)
