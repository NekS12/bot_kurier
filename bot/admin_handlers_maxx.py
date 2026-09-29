from datetime import datetime
import sqlite3
from typing import List

import aiomax
from aiomax import Bot, Router
from aiomax.types import Message, LocationAttachment
import aiomax.buttons as buttons
import aiomax.filters as filters
from aiomax.fsm import FSMCursor

from config import ADMIN_ID
from database import get_all_users, get_orders, get_orders_by_status

DB_NAME = 'dostavkin.db'
USERS_DB = "users.db"

router = Router()

# --------------------------
# FSM состояния (строки)
# --------------------------
STATE_WAITING_FOR_DATE = "waiting_for_date"

# --------------------------
# Клавиатуры
# --------------------------
def create_reply_keyboard(buttons_list: List[List[str]]) -> buttons.KeyboardBuilder:
    kb = buttons.KeyboardBuilder()
    for row in buttons_list:
        kb.row(*[buttons.MessageButton(text=text) for text in row])
    return kb

admin_main_kb = create_reply_keyboard([
    ["Основное"]
])

restaurants_kb = create_reply_keyboard([
    ["📦 Количество заказов", "📋 Статусы заказов"],
    ["🚴 Курьеры", "🛰 Геолокация курьеров"],
    ["📊 Итоговый заработок"],
    ["🔙 Назад в админ-панель"]
])

# --------------------------
# Хендлеры
# --------------------------
@router.on_message("/admin")
async def admin_panel(message: Message):
    if message.sender.user_id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа")
        return
    await message.answer("👑 Админ-панель", keyboard=admin_main_kb)


@router.on_message("Основное")
async def my_restaurants(message: Message):
    if message.sender.user_id != ADMIN_ID:
        return
    await message.answer("📍 Выберите действие:", keyboard=restaurants_kb)


@router.on_message("🔙 Назад в админ-панель")
async def back_to_admin(message: Message):
    if message.sender.user_id != ADMIN_ID:
        return
    await message.answer("👑 Админ-панель", keyboard=admin_main_kb)


@router.on_message("🚴 Курьеры")
async def admin_couriers(message: Message):
    if message.sender.user_id != ADMIN_ID:
        return

    users = await get_all_users()
    orders = await get_orders()

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
    await message.answer(text, format="markdown")


@router.on_message("🛰 Геолокация курьеров")
async def courier_locations(message: Message, bot: Bot):
    if message.sender.user_id != ADMIN_ID:
        return

    users = await get_all_users()
    has_location = False

    for u in users:
        user_id, name, phone, lat, lon, _ = u
        if lat is not None and lon is not None:
            loc = LocationAttachment(latitude=float(lat), longitude=float(lon))
            await bot.send_message(
                text=f"📍 {name}\n📞 Телефон: {phone}",
                chat_id=message.recipient.chat_id,
                attachments=[loc]
            )
            has_location = True

    if not has_location:
        await message.answer("❌ Ни один курьер пока не отправил геопозицию")


@router.on_message("📋 Статусы заказов")
async def orders_status(message: Message):
    if message.sender.user_id != ADMIN_ID:
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_name, client_phone, courier_name, status, address
        FROM orders
        WHERE courier IS NOT NULL AND courier_name != ''
    """)
    orders_info = cur.fetchall()
    conn.close()

    if not orders_info:
        await message.answer("📭 Нет заказов, закреплённых за курьерами.")
        return

    text = "📋 <b>Заказы, закреплённые за курьерами:</b>\n\n"
    for order in orders_info:
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
    await message.answer(text, format="html")

    all_orders = await get_orders()
    if not all_orders:
        return

    text = "📋 Статусы заказов:\n\n"
    for o in all_orders:
        order_id, status, courier_id = o
        text += f"🆔 Заказ {order_id} | Статус: {status}\n"
    await message.answer(text)


@router.on_message("📦 Количество заказов")
async def total_completed_orders(message: Message, cursor: FSMCursor):
    if message.sender.user_id != ADMIN_ID:
        return

    completed_orders = await get_orders_by_status("Доставлено")
    total_completed = len(completed_orders)
    await message.answer(f"✅ Количество выполненных заказов: {total_completed}")

    await message.answer("Введите дату в формате YYYY-MM-DD, чтобы увидеть выполненные заказы за эту дату:")
    await cursor.change_state(STATE_WAITING_FOR_DATE)


@router.on_message(filters.state(STATE_WAITING_FOR_DATE))
async def orders_by_date(message: Message, cursor: FSMCursor):
    if message.sender.user_id != ADMIN_ID:
        return

    date_text = message.body.text.strip()

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
        await cursor.clear()
        return

    text = f"📦 Доставленные заказы на {date_text}:\n\n"
    for order_id, client_name, courier_id, order_date, address in orders:
        conn = sqlite3.connect(USERS_DB)
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

    await message.answer(text, format="html")
    await cursor.clear()


@router.on_message("📊 Итоговый заработок")
async def total_earnings(message: Message):
    if message.sender.user_id != ADMIN_ID:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, order_count FROM users")
    users = cur.fetchall()

    if not users:
        await message.answer("❌ Нет данных о курьеров")
        return

    text = "💰 <b>Итоговый заработок курьеров</b>\n\n"
    for courier_id, name, total_sum in users:
        cur.execute("SELECT SUM(amount) FROM earnings WHERE courier_id=? AND date=?", (courier_id, today))
        day_sum = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(amount) FROM earnings WHERE courier_id=? AND date LIKE ?", (courier_id, f"{month}%"))
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
    await message.answer(text, format="html")
