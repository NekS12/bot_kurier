import sqlite3
import asyncio
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

DB_NAME = "users.db"

def get_user_keyboard(user_id: int):
    """Возвращает клавиатуру в зависимости от статуса смены"""

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT shift_status FROM users WHERE id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()

    shift_active = result and result[0] == "Активен"

    # Базовые кнопки
    buttons = [
        [KeyboardButton(text="🛒 Работа с заказами")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📍 Отправить геопозицию", request_location=True)]
    ]

    # Если смена открыта — добавляем кнопку "Закрыть смену"
    if shift_active:
        buttons.append([KeyboardButton(text="❌ Закрыть смену")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


async def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            order_count TEXT,
            shift_status TEXT DEFAULT 'Неактивен'
        )
    """)


    cur.execute("""
               CREATE TABLE IF NOT EXISTS orders (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   status TEXT NOT NULL,
                   courier_id INTEGER,
                   order_date TEXT,
                   FOREIGN KEY (courier_id) REFERENCES users (id)
               )
           """)

    cur.execute("""
            CREATE TABLE IF NOT EXISTS orders_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                quantity INTEGER NOT NULL
            )
        """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS iiko_orders (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            order_date TEXT,
            sum REAL,
            address TEXT,
            courier_id INTEGER,
            FOREIGN KEY (courier_id) REFERENCES users (id)
        )
    """)

    cur.execute("""
            CREATE TABLE IF NOT EXISTS earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                courier_id INTEGER,
                amount REAL,
                date TEXT
            )
        """)

    conn.commit()
    conn.close()


async def set_shift_status(user_id: int, status: str):
    """Обновляет статус смены ('Активен' или 'Неактивен')"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET shift_status = ? WHERE id = ?",
        (status, user_id)
    )
    conn.commit()
    conn.close()

async def get_active_couriers():
    """Возвращает список ID всех курьеров с активной сменой"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE shift_status = 'Активен'")
    result = [row[0] for row in cur.fetchall()]
    conn.close()
    return result


async def get_orders_by_status(status: str):
    """Возвращает все заказы по заданному статусу"""
    import sqlite3
    conn = sqlite3.connect("dostavkin.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status = ?", (status,))
    result = cur.fetchall()
    conn.close()
    return result


async def add_user(user_id: int, name: str, phone: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (id, name, phone, latitude, longitude, order_count) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, phone, None, None, "0")  # по умолчанию 0 выполненных заказов
    )
    conn.commit()
    conn.close()


async def update_location(user_id: int, latitude: float, longitude: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET latitude=?, longitude=? WHERE id=?",
        (latitude, longitude, user_id)
    )
    conn.commit()
    conn.close()

async def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, latitude, longitude, order_count FROM users WHERE id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    if result and result[5] is None:
        result = result[:5] + ("0",)  # если order_count пустой → 0
    return result

async def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, latitude, longitude, order_count FROM users")
    result = cur.fetchall()
    conn.close()
    return result

async def get_orders():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders")
    result = cur.fetchall()
    conn.close()
    return result



async def get_orders_by_courier(courier_id: str):
    """Все заказы курьера"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE courier_id=?", (courier_id,))
    result = cur.fetchall()
    conn.close()
    return result


async def get_orders_by_date(date: str, courier_id: str = None):
    """Все заказы на дату (для всех или конкретного курьера)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if courier_id:
        cur.execute("SELECT * FROM orders WHERE order_date=? AND courier_id=?", (date, courier_id))
    else:
        cur.execute("SELECT * FROM orders WHERE order_date=?", (date,))

    result = cur.fetchall()
    conn.close()
    return result


async def get_order_stats(courier_id: str = None):
    """Статистика заказов (всего, выполненные, в пути)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if courier_id:
        cur.execute("SELECT COUNT(*) FROM orders WHERE courier_id=?", (courier_id,))
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Closed' AND courier_id=?", (courier_id,))
        done = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='OnWay' AND courier_id=?", (courier_id,))
        on_way = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM orders")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Closed'")
        done = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='OnWay'")
        on_way = cur.fetchone()[0]

    conn.close()
    return {"total": total, "done": done, "on_way": on_way}

async def save_iiko_order(order: dict):
    """Сохраняет или обновляет заказ из iiko"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO iiko_orders (id, status, order_date, sum, address, courier_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            order_date=excluded.order_date,
            sum=excluded.sum,
            address=excluded.address,
            courier_id=excluded.courier_id
    """, (
        order["id"],
        order.get("status"),
        order.get("order_date"),
        order.get("sum"),
        order.get("address"),
        order.get("courier_id"),
    ))
    conn.commit()
    conn.close()


async def get_iiko_orders():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM iiko_orders")
    rows = cur.fetchall()
    conn.close()
    return rows

