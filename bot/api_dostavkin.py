import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sqlite3
import os
from aiogram import Bot
from config import BOT_TOKEN
from dotenv import load_dotenv
import re
from config import ADMIN_ID

load_dotenv()

DB_NAME = "dostavkin.db"
bot = Bot(token=BOT_TOKEN)

last_orders = {}  # id: status


# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            client_name TEXT,
            client_phone TEXT,
            address TEXT,
            payment_method TEXT,
            status TEXT,
            order_date TEXT,
            courier TEXT,
            courier_name TEXT,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()


# --- ПОЛУЧЕНИЕ АКТИВНЫХ КУРЬЕРОВ ---
def get_active_couriers():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE shift_status = 'Активен'")
        ids = [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError:
        ids = []
    conn.close()
    return ids


# --- КЛАСС API ---
class DostavkinAPI:
    def __init__(self):
        self.base_url = "https://admin.dostavkin72.ru"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def login(self):
        """Авторизация через переменные окружения"""
        email = os.getenv("DOSTAVKIN_EMAIL")
        password = os.getenv("DOSTAVKIN_PASSWORD")
        if not email or not password:
            raise Exception("⛔ Не заданы переменные DOSTAVKIN_EMAIL и DOSTAVKIN_PASSWORD")

        async with self.session.get(f"{self.base_url}/login") as resp:
            html_code = await resp.text()
            soup = BeautifulSoup(html_code, "html.parser")
            token = soup.find("input", {"name": "_token"})
            if not token:
                raise Exception("CSRF токен не найден")
            csrf_token = token["value"]

        data = {"_token": csrf_token, "email": email, "password": password}

        async with self.session.post(f"{self.base_url}/login", data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Ошибка логина: {resp.status}\n{text}")
            print("✅ Авторизация прошла успешно!")

    async def fetch_orders_json(self, limit=10):
        """Получает JSON с основными данными заказов"""
        url = (
            f"{self.base_url}/orders?draw=1"
            "&columns[0][data]=id"
            "&columns[1][data]=created_at"
            "&columns[2][data]=restaurant.name"
            "&columns[3][data]=order_status.status"
            "&columns[4][data]=payment.price"
            "&columns[5][data]=hint"
            "&columns[6][data]=payment.method"
            "&columns[7][data]=active"
            "&columns[8][data]=action"
            "&order[0][column]=0&order[0][dir]=desc"
            f"&start=0&length={limit}&search[value]="
        )

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/orders",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0",
        }

        async with self.session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Ошибка получения списка заказов: {resp.status}")
            data = await resp.json()
            return data

    async def fetch_order_details(self, order_id: int):
        """Парсит HTML страницы конкретного заказа и достаёт все ключевые поля"""
        url = f"{self.base_url}/orders/{order_id}"
        headers = {
            "Referer": f"{self.base_url}/orders",
            "User-Agent": "Mozilla/5.0",
        }

        async with self.session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Ошибка загрузки заказа #{order_id}: {resp.status}")
            html_code = await resp.text()

        soup = BeautifulSoup(html_code, "html.parser")

        def extract_field(label_text):
            """Находит значение рядом с меткой <label>"""
            label = soup.find("label", string=re.compile(label_text, re.IGNORECASE))
            if not label:
                return ""
            value = label.find_next("p") or label.find_next("div", class_="col-sm-9")
            return value.get_text(strip=True) if value else ""

        order = {
            "id": order_id,
            "client_name": extract_field("Клиент"),
            "client_phone": extract_field("Номер телефона"),
            "address": extract_field("адрес доставки"),
            "payment_method": extract_field("Метод"),
            "status": extract_field("Статус"),
            "order_date": extract_field("Дата заказа"),
            "courier": extract_field("Курьер"),
            "description": extract_field(r"Заметка[:]?"),  # <-- точное соответствие
        }

        # Убираем системные фразы
        if not order["courier"] or "Заказы" in order["courier"]:
            order["courier"] = ""

        print(f"🧩 Детали #{order_id}: {order}")
        return order


# --- СОХРАНЕНИЕ ЗАКАЗА ---
def save_order(details: dict):
    """Сохраняет заказ в БД"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 🔥 Преобразуем метод оплаты
    payment = details.get("payment_method", "")
    if payment.lower().strip() in ("наличными курьеру", "наличными"):
        payment = "Оплата по договору"

    cur.execute("""
        INSERT OR REPLACE INTO orders
        (id, client_name, client_phone, address, payment_method, status, order_date, courier, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        details.get("id"),
        details.get("client_name"),
        details.get("client_phone"),
        details.get("address"),
        payment,  # <-- уже замененное значение
        details.get("status"),
        details.get("order_date"),
        details.get("courier"),
        details.get("description")
    ))
    conn.commit()
    conn.close()
    print(f"💾 Заказ #{details.get('id')} сохранён в БД.")




# --- ОБНОВЛЕНИЕ ЗАКАЗОВ ---
async def update_orders():
    """Обновляет заказы, уведомляет курьеров о новых и изменившихся"""
    global last_orders
    init_db()

    async with DostavkinAPI() as api:
        try:
            await api.login()
            data = await api.fetch_orders_json(limit=20)

            print(f"\n📦 Найдено заказов: {data['recordsTotal']}\n")

            current_orders = {}
            for item in data["data"]:
                raw_id = str(item.get("id", "")).replace("#", "").strip()
                status = (
                    item.get("order_status", {}).get("status")
                    if isinstance(item.get("order_status"), dict)
                    else item.get("order_status.status") or ""
                )
                if raw_id.isdigit():
                    current_orders[raw_id] = status

            # --- Проверяем новые заказы ---
            new_orders = set(current_orders.keys()) - set(last_orders.keys())
            if new_orders:
                print(f"🚀 Новые заказы: {new_orders}")

                for oid in new_orders:
                    try:
                        order_id = int(oid)

                        # ✅ Проверка: если заказ уже есть — не сохраняем
                        if order_exists(order_id):
                            print(f"⏩ Заказ #{order_id} уже есть в БД — пропуск.")
                            continue

                        details = await api.fetch_order_details(order_id)
                        save_order(details)
                        print(f"💾 Новый заказ #{order_id} сохранён в БД.")

                        # --- Рассылаем уведомление всем активным курьерам ---
                        couriers = get_active_couriers()
                        if couriers:
                            payment = details.get("payment_method", "")
                            if payment.lower().strip() in ("наличными курьеру", "наличными"):
                                payment = "Оплата по договору"

                            msg = (
                                f"🆕 <b>Новый заказ #{order_id}</b>\n"
                                f"👤 Клиент: {details.get('client_name') or '—'}\n"
                                f"📍 Адрес: {details.get('address') or '—'}\n"
                                f"💳 Оплата: {payment}\n"
                                f"📝 Заметка: {details.get('description') or '—'}\n\n"
                                f"❗ Заказ доступен для принятия в разделе «🔓 Открытые заказы»"
                            )

                            admin_msg = (
                                f"📦 <b>Поступил новый заказ #{order_id}</b>\n\n"
                                f"👤 Клиент: {details.get('client_name') or '—'}\n"
                                f"☎ Телефон: {details.get('client_phone') or '—'}\n"
                                f"📍 Адрес: {details.get('address') or '—'}\n"
                                f"💳 Оплата: {payment}\n"
                                f"📝 Заметка: {details.get('description') or '—'}\n"
                                f"⏰ Время: {details.get('order_date') or '—'}"
                            )

                            for cid in couriers:
                                try:
                                    await bot.send_message(cid, msg, parse_mode="HTML")
                                except Exception as e:
                                    print(f"⚠️ Ошибка уведомления {cid}: {e}")
                            else:
                                print("⚠️ Нет активных курьеров для уведомления.")

                            try:
                                await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
                            except Exception as e:
                                print(f"⚠️ Ошибка уведомления админа: {e}")



                    except Exception as e:
                        print(f"⚠️ Ошибка при обработке нового заказа #{oid}: {e}")

            # --- Проверяем изменение статусов ---
            changed_orders = {
                oid: current_orders[oid]
                for oid in current_orders
                if oid in last_orders and current_orders[oid] != last_orders[oid]
            }

            for oid, new_status in changed_orders.items():
                old_status = last_orders[oid]
                if old_status.lower() in ("новый", "создан") and new_status.lower() in ("в пути", "принят", "назначен"):
                    couriers = get_active_couriers()
                    for cid in couriers:
                        try:
                            await bot.send_message(
                                cid,
                                f"🚗 Заказ №{oid} уже взят другим курьером"
                            )
                        except Exception as e:
                            print(f"⚠️ Ошибка отправки уведомления {cid}: {e}")

            # Обновляем состояние
            last_orders = current_orders

        except Exception as e:
            print(f"⚠️ Ошибка при обновлении заказов: {e}")

        print("✅ Обновление завершено.")




def order_exists(order_id: int) -> bool:
    """Проверяет, есть ли заказ в БД"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists
