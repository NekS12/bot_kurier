from aiomax import buttons

# Кнопка для отправки номера
request_phone_kb = buttons.KeyboardBuilder()
request_phone_kb.row(
    buttons.MessageButton(text="📱 Отправить номер", request_contact=True)
)

# Админ-панель
admin_kb = buttons.KeyboardBuilder()
admin_kb.row(buttons.MessageButton(text="📋 Список пользователей"))
admin_kb.row(buttons.MessageButton(text="📍 Курьеры на карте"))
admin_kb.row(buttons.MessageButton(text="🔍 Поиск по ID"))
admin_kb.row(buttons.MessageButton(text="🚪 Выйти"))

# Меню для обычных пользователей (закомментировано)
# user_kb = buttons.KeyboardBuilder()
# user_kb.row(buttons.MessageButton(text="🛒 Работа с заказами"))
# user_kb.row(buttons.MessageButton(text="👤 Профиль"))
# user_kb.row(buttons.MessageButton(text="📍 Отправить геопозицию", request_location=True))

# Клавиатура для курьера
courier_orders_kb = buttons.KeyboardBuilder()
courier_orders_kb.row(
    buttons.MessageButton(text="📅 Мои заказы"),
    buttons.MessageButton(text="🔓 Открытые заказы")
)
courier_orders_kb.row(
    buttons.MessageButton(text="🆘 Помощь"),
    buttons.MessageButton(text="💬 Обратная связь")
)
courier_orders_kb.row(buttons.MessageButton(text="👤 Профиль"))
courier_orders_kb.row(buttons.MessageButton(text="🔙 Назад в меню"))

# Клавиатура статуса
status_kb = buttons.KeyboardBuilder()
status_kb.row(buttons.MessageButton(text="Открыть смену"))
