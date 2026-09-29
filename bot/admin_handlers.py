from datetime import datetime
import sqlite3

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID
from database import get_all_users, get_orders, get_orders_by_status

DB_NAME ='dostavkin.db'

router = Router()

class OrdersByDateState(StatesGroup):

    waiting_for_date = State()



# ====== Клавиатуры ======
admin_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Основное")],
        #[KeyboardButton(text="📊 Статистика")]
    ],
    resize_keyboard=True
)

restaurants_kb = ReplyKeyboardMarkup(
    keyboard=[
        # Верхняя секция
        [KeyboardButton(text="📦 Количество заказов"), KeyboardButton(text="📋 Статусы заказов")],

        # Средняя секция
        [KeyboardButton(text="🚴 Курьеры"), KeyboardButton(text="🛰 Геолокация курьеров")],

        # Нижняя секция
        [KeyboardButton(text="📊 Итоговый заработок")],

        # Назад
        [KeyboardButton(text="🔙 Назад в админ-панель")]
    ],
    resize_keyboard=True
)
'''Не забыть прописать для гпт Итоговый заработок'''

# ====== Команды ======
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа")
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_main_kb)

# ====== Мои рестораны ======
@router.message(F.text == "Основное")
async def my_restaurants(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📍 Выберите действие:", reply_markup=restaurants_kb)

# ====== Назад ======
@router.message(F.text == "🔙 Назад в админ-панель")
async def back_to_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_main_kb)


# ====== Курьеры ======
@router.message(F.text == "🚴 Курьеры")
async def admin_couriers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = await get_all_users()  # [(id, name, phone, lat, lon, order_sum), ...]
    orders = await get_orders()    # [(order_id, status, courier_id), ...]

    # Подсчёт количества заказов на курьера
    courier_orders_count = {}
    for o in orders:
        courier_id = o[2]
        if courier_id:
            courier_orders_count[courier_id] = courier_orders_count.get(courier_id, 0) + 1

    if not users:
        await message.answer("❌ Курьеров нет в базе")
        return

    text = "🚴 Курьеры:\n\n"
    for u in users:
        user_id, name, phone, lat, lon, order_sum = u
        count = courier_orders_count.get(user_id, 0)

        text += (
            f"👤 *{name}*\n"
            f"📞 {phone}\n"
            f"📦 Заказов: {count}\n"
            f"💰 Сумма заказов: {order_sum}\n"
            f"🆔 ID: `{user_id}`\n"
            "─────────────\n"
        )

    await message.answer(text, parse_mode="Markdown")


#=====Геолокация Курьеров=======
@router.message(F.text == "🛰 Геолокация курьеров")
async def courier_locations(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = await get_all_users()  # [(id, name, phone, latitude, longitude), ...]
    has_location = False

    for u in users:
        user_id, name, phone, lat, lon, _ = u
        if lat is not None and lon is not None:
            await message.bot.send_location(message.chat.id, latitude=lat, longitude=lon)
            await message.answer(f"📍 {name}\n 📍Телефон: {phone}")
            has_location = True

    if not has_location:
        await message.answer("❌ Ни один курьер пока не отправил геопозицию")


#=====Статусы заказов====
@router.message(F.text == "📋 Статусы заказов")
async def orders_status(message: Message):
    """Показывает заказы, закреплённые за курьерами"""
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_name, client_phone, courier_name, status, address
        FROM orders
        WHERE courier IS NOT NULL AND courier_name != ''
    """)
    orders = cur.fetchall()
    conn.close()

    if not orders:
        await message.answer("📭 Нет заказов, закреплённых за курьерами.")
        return

    text = "📋 <b>Заказы, закреплённые за курьерами:</b>\n\n"
    for order in orders:
        order_id, client_name, client_phone, courier_name, status, address = order
        text += (
            f"🆔 Заказ #{order_id}\n"
            f"👤 Клиент: {client_name or '—'}\n"
            f"📞 Телефон {client_phone}\n"
            f"🚗 Курьер: {courier_name}\n"
            f"📦 Статус: {status or 'Не указан'}\n"
            f"📍 Адрес: {address or '—'}\n"
            "———————————————\n"
        )

    await message.answer(text, parse_mode="HTML")

    orders = await get_orders()  # [(id, status, courier_id), ...]
    if not orders:
        return

    text = "📋 Статусы заказов:\n\n"
    for o in orders:
        order_id, status, courier_id = o
        text += f"🆔 Заказ {order_id} | Статус: {status}\n"

    await message.answer(text)


# ====== Количество заказов ======
@router.message(F.text == "📦 Количество заказов")
async def total_completed_orders(message: Message, state: FSMContext):
    """Показывает количество выполненных заказов и предлагает выбрать дату"""
    if message.from_user.id != ADMIN_ID:
        return

    # Получаем все заказы со статусом "Выполнен"
    completed_orders = await get_orders_by_status("Доставлено")
    total_completed = len(completed_orders)

    await message.answer(f"✅ Количество выполненных заказов: {total_completed}")

    await message.answer("Введите дату в формате YYYY-MM-DD, чтобы увидеть выполненные заказы за эту дату:")
    await state.set_state(OrdersByDateState.waiting_for_date)

# ====== Обработка введённой даты ======
@router.message(OrdersByDateState.waiting_for_date)
async def orders_by_date(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    date_text = message.text.strip()  # формат YYYY-MM-DD

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_name, courier, order_date, address
        FROM orders
        WHERE status = 'Доставлено' AND order_date LIKE ?
        ORDER BY order_date DESC
    """, (date_text + "%",))
    orders = cur.fetchall()
    conn.close()

    if not orders:
        await message.answer(f"❌ Доставленных заказов на {date_text} нет")
        await state.clear()
        return

    text = f"📦 Доставленные заказы на {date_text}:\n\n"

    for order_id, client_name, courier_id, order_date, address in orders:

        # Получаем имя курьера по ID
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT name FROM users WHERE id=?", (courier_id,))
        row = cur.fetchone()
        conn.close()

        courier_name = row[0] if row else "Не назначен"

        text += (
            f"🆔 Заказ #{order_id}\n"
            f"👤 Клиент: {client_name or '—'}\n"
            f"🚗 Курьер: {courier_name}\n"
            f"📍 Адрес: {address or '—'}\n"
            f"📅 Дата: {order_date}\n"
            "———————————————\n"
        )

    await message.answer(text, parse_mode="HTML")
    await state.clear()

from aiogram import Router, F
from aiogram.types import Message
import sqlite3


USERS_DB = "users.db"


@router.message(F.text == "📊 Итоговый заработок")
async def total_earnings(message: Message):
    """Показывает заработок курьеров: за день, за месяц и всего."""

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()

    # Получаем курьеров
    cur.execute("SELECT id, name, order_count FROM users")
    users = cur.fetchall()

    if not users:
        await message.answer("❌ Нет данных о курьерах")
        return

    text = "💰 <b>Итоговый заработок курьеров</b>\n\n"

    for courier_id, name, total_sum in users:

        # Заработок за день
        cur.execute("SELECT SUM(amount) FROM earnings WHERE courier_id=? AND date=?",
                    (courier_id, today))
        day_sum = cur.fetchone()[0] or 0

        # Заработок за месяц
        cur.execute("SELECT SUM(amount) FROM earnings WHERE courier_id=? AND date LIKE ?",
                    (courier_id, f"{month}%"))
        month_sum = cur.fetchone()[0] or 0

        total_sum = total_sum or 0

        text += (
            f"👤 <b>{name}</b>\n"
            f"📅 Сегодня: <b>{day_sum} ₽</b>\n"
            f"🗓 Месяц: <b>{month_sum} ₽</b>\n"
            f"💼 Всего: <b>{total_sum} ₽</b>\n"
            "———————————————\n"
        )

    conn.close()

    await message.answer(text, parse_mode="HTML")
