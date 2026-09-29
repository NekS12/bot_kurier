from datetime import datetime
import urllib
import aiogram
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_member import USERS

from keyboards import status_kb
from database import add_user, get_user, update_location, get_all_users, get_orders, set_shift_status, get_user_keyboard
from keyboards import request_phone_kb, admin_kb,  courier_orders_kb
from config import ADMIN_ID
import sqlite3
import admin_handlers as ad
router = Router()

class CompleteOrderState(StatesGroup):
    waiting_for_sum = State()

USERS_DB='users.db'


# Кнопка под каждым заказом
def complete_button(order_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Заказ выполнен", callback_data=f"complete_order:{order_id}")]
    ])
    return kb


# FSM для регистрации
class RegState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


class AdminState(StatesGroup):
    waiting_for_search_id = State()

class HistoryStates(StatesGroup):
    waiting_for_date = State()


# ====== Старт ======
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Добро пожаловать в админ-панель", reply_markup=ad.admin_main_kb)
        return
    user_id = message.sender.user_id
    print("PROFILE HANDLER TELEGRAM")
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(f"Привет, {user[1]}! Ты уже зарегистрирован ✅", reply_markup=get_user_keyboard(user_id))
    else:
        await message.answer("Привет! Давай начнем регистрацию.\nНапиши своё имя 👇")
        await state.set_state(RegState.waiting_for_name)


# ====== Регистрация ======
@router.message(RegState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь отправь свой номер телефона 👇", reply_markup=request_phone_kb)
    await state.set_state(RegState.waiting_for_phone)


@router.message(RegState.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = message.contact.phone_number

    await add_user(message.from_user.id, name, phone)
    user_id = message.from_user.id

    await message.answer(
        f"✅ Регистрация завершена!\nИмя: {name}\nТелефон: {phone}\n\nПеред работой с заказами нужно отправить свою геопозицию по кнопке внизу.",
        reply_markup=get_user_keyboard(user_id)
    )
    await state.clear()


# ====== Геопозиция ======
@router.message(F.location)
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    await update_location(message.from_user.id, lat, lon)

    if message.location.live_period:  # live location
        await message.answer("📡 Твоя геопозиция транслируется и обновляется в базе")
    else:
        await message.answer("✅ Геопозиция сохранена в базе")


# ====== Админ-панель ======
@router.message(F.text == "📋 Список пользователей")
async def admin_list_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone FROM users")
    users = cur.fetchall()
    conn.close()

    if not users:
        await message.answer("❌ В базе нет пользователей")
    else:
        text = "👥 Пользователи:\n\n"
        for u in users:
            text += f"🆔 {u[0]} | {u[1]} | {u[2]}\n"
        await message.answer(text)


@router.message(F.text == "📍 Курьеры на карте")
async def admin_list_couriers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = await get_all_users()
    couriers = [u for u in users if u[3] and u[4]]

    if not couriers:
        await message.answer("❌ Курьеры пока не отправили геопозицию")
        return

    text = "🚚 Курьеры с геопозицией:\n\n"
    for u in couriers:
        text += f"🆔 {u[0]} | {u[1]} | {u[2]}\n🌍 {u[3]}, {u[4]}\n\n"
    await message.answer(text)

    for u in couriers:
        await message.bot.send_location(message.chat.id, latitude=u[3], longitude=u[4])


@router.message(F.text == "🔍 Поиск по ID")
async def admin_search_user(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Введите ID пользователя:")
    await state.set_state(AdminState.waiting_for_search_id)


@router.message(AdminState.waiting_for_search_id)
async def admin_process_search(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await get_user(user_id)
        if user:
            await message.answer(f"✅ Найден:\nID: {user[0]}\nИмя: {user[1]}\nТелефон: {user[2]}")
        else:
            await message.answer("❌ Пользователь не найден")
    except ValueError:
        await message.answer("⚠️ Введите корректный ID (число)")
    await state.clear()


@router.message(F.text == "🚪 Выйти")
async def admin_exit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    user_id = message.from_user.id
    await message.answer("Вы вышли из админ-панели", reply_markup=get_user_keyboard(user_id))


# ====== Работа с заказами ======
@router.message(F.text == "🛒 Работа с заказами")
async def courier_orders(message: Message):
    if message.from_user.id == ADMIN_ID:
        return  # админ сюда не попадает
    await message.answer("📲 Панель работы курьера:", reply_markup=status_kb)

@router.message(F.text == "Открыть смену")
async def orders_do(message:Message):
    if message.from_user.id == ADMIN_ID:
        return

    await set_shift_status(message.from_user.id, "Активен")
    await message.answer("✅Вы открыли смену, Не забудь зыкрыть ее в конце дня.", reply_markup=courier_orders_kb)


@router.message(F.text == "❌ Закрыть смену")
async def close_shift(message: Message):
    user_id = message.from_user.id

    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("UPDATE users SET shift_status = 'Неактивен' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    await message.answer(
        "🔒 Смена закрыта. Хорошего отдыха!",
        reply_markup=get_user_keyboard(user_id)
    )


@router.message(F.text == "🔙 Назад в меню")
async def back_to_menu(message: Message):
    if message.from_user.id == ADMIN_ID:
        return
    user_id = message.from_user.id
    await message.answer("⬅ Главное меню", reply_markup=get_user_keyboard(user_id))

# ====== Мои смены ======
@router.message(F.text == "📅 Мои заказы")
async def my_orders(message: Message):
    courier_id = message.from_user.id

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_name, client_phone, address, payment_method, status, order_date
        FROM orders
        WHERE courier = ? AND status NOT IN ('Выполнен', 'Доставлено')
        ORDER BY order_date DESC
    """, (courier_id,))
    orders = cur.fetchall()
    conn.close()

    if not orders:
        await message.answer("😕 У вас пока нет активных заказов.")
        return

    for order in orders:
        order_id, client_name, client_phone, address, payment_method, status, order_date = order
        text = (
            f"🆔 <b>Заказ #{order_id}</b>\n"
            f"👤 Клиент: {client_name or 'Не указан'}\n"
            f"📞 Телефон {client_phone}\n"
            f"📍 Адрес: {address or 'Не указан'}\n"
            f"💰 Оплата: {payment_method or 'Не указана'}\n"
            f"📦 Статус: {status or 'Не указан'}\n"
            f"📅 Дата: {order_date or '-'}\n"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=complete_button(order_id))



# --- Обработка кнопки "✅ Заказ выполнен" ---
@router.callback_query(F.data.startswith("complete_order:"))
async def complete_order_callback(callback: CallbackQuery):
    order_id = callback.data.split(":")[1]
    courier_id = callback.from_user.id
    amount = 200  # фиксированная ставка за заказ

    # Получаем имя курьера
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE id=?", (courier_id,))
    courier_name = cur.fetchone()
    courier_name = courier_name[0] if courier_name else "Неизвестный курьер"
    conn.close()

    # Обновляем статус заказа
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = 'Доставлено' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    # Добавляем сумму курьеру
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT order_count FROM users WHERE id=?", (courier_id,))
    row = cur.fetchone()
    new_sum = (float(row[0]) if row and row[0] else 0) + amount
    cur.execute("UPDATE users SET order_count=? WHERE id=?", (new_sum, courier_id))
    conn.commit()

    # Записываем в историю
    date = datetime.now().strftime("%Y-%m-%d")
    cur.execute("INSERT INTO earnings (courier_id, amount, date) VALUES (?, ?, ?)", (courier_id, amount, date))
    conn.commit()
    conn.close()

    await callback.message.delete()

    # Сообщение курьеру
    await callback.message.answer(
        f"✅ Заказ #{order_id} завершён и убран из ваших активных.",
        parse_mode="HTML"
    )

    # Уведомление админу
    await callback.bot.send_message(
        ADMIN_ID,
        f"✅ Курьер <b>{courier_name}</b> завершил заказ #{order_id}",
        parse_mode="HTML"
    )

    # Закрываем алерт кнопки
    await callback.answer()



# ====== Открытые смены ======
DB_NAME = "dostavkin.db"

def get_new_orders():
    """Получает все новые заказы из БД (включая заказы без статуса)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, client_name, address, payment_method, description
        FROM orders
        WHERE
            (status IS NULL OR status = '' OR status = 'Заявка принята' OR status = 'Новый')
            AND (courier IS NULL OR courier = '' OR courier = 'Не назначен')
        ORDER BY id DESC
    """)

    orders = cur.fetchall()
    conn.close()
    return orders


@router.message(F.text == "🔓 Открытые заказы")
async def open_orders(message: Message):
    """Выводит список доступных заказов"""
    orders = get_new_orders()

    if not orders:
        await message.answer("🟢 Нет доступных заказов на данный момент.")
        return

    for order in orders:
        order_id, client_name, address, payment, description = order

        text = (
            f"📦 <b>Заказ #{order_id}</b>\n"
            f"👤 Клиент: {client_name or '—'}\n"
            f"📍 Адрес: {address or '—'}\n"
            f"💳 Оплата: {payment or '—'}\n"
            f"Заметка: {description or'-'}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Взять заказ", callback_data=f"take_order:{order_id}")]
        ])

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("take_order:"))
async def take_order_callback(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    courier_id = callback.from_user.id

    # Получаем имя курьера
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE id=?", (courier_id,))
    row = cur.fetchone()
    courier_name = row[0] if row else "Неизвестный курьер"
    conn.close()

    # Получаем адрес заказа
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT address FROM orders WHERE id=?", (order_id,))
    result = cur.fetchone()
    if not result:
        await callback.answer("⚠️ Заказ не найден.", show_alert=True)
        conn.close()
        return

    address = result[0] or "Адрес не указан"

    # Обновляем заказ
    cur.execute("""
        UPDATE orders
        SET status = 'В пути',
            courier = ?,         -- здесь храним ID
            courier_name = ?     -- здесь храним имя
        WHERE id = ?
    """, (courier_id, courier_name, order_id))
    conn.commit()
    conn.close()

    # Отправляем сообщение
    link_2gis = f"https://2gis.ru/tyumen/search/{urllib.parse.quote(address)}"

    await callback.message.edit_text(
        f"✅ Заказ #{order_id} теперь закреплён за вами.\n"
        f"📍 Адрес доставки: {address}\n\n"
        f"🗺️ <a href='{link_2gis}'>Открыть в 2ГИС</a>\n\n"
        f"Статус: <b>В пути</b>",
        parse_mode="HTML"
    )

    await callback.answer("Вы взяли заказ 🚗")

    # Уведомление админу
    await callback.bot.send_message(
        ADMIN_ID,
        f"📦 Курьер <b>{courier_name}</b> взял заказ #{order_id}",
        parse_mode="HTML"
    )



# ====== История ======


@router.message(HistoryStates.waiting_for_date)
async def filter_orders_by_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    date_text = message.text.strip()

    orders = await get_orders()
    user_orders = [o for o in orders if o[2] == user_id and o[3] == date_text]  # o[3] = order_date

    if not user_orders:
        await message.answer(f"Заказы на дату {date_text} не найдены.")
    else:
        text = f"📅 Заказы на {date_text}:\n"
        for o in user_orders:
            text += f"- Заказ ID: {o[0]}, Статус: {o[1]}\n"
        await message.answer(text)

    await state.clear()

# ====== Помощь ======
@router.message(F.text == "🆘 Помощь")
async def help_courier(message: Message):
    await message.answer("🆘 Здесь будет информация по работе курьера.\n\n Не забывайте закрыть смену в конце рабочего дня.")

# ====== Обратная связь ======
@router.message(F.text == "💬 Обратная связь")
async def feedback(message: Message):
    await message.answer("💬 Здесь можно будет отправить сообщение менеджеру.\n\n@pobedaexpresstgm")


@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    # user = (id, name, phone, latitude, longitude, orders_count)
    user_id, name, phone, latitude, longitude, orders_count = user

    orders_count_text = orders_count if orders_count else "0"

    text = (
        f"👤 Профиль курьера:\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Выполнено заказов на сумму: {orders_count}"
    )

    await message.answer(text)
