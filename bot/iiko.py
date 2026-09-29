import aiohttp


BASE_URL = "https://api-ru.iiko.services"
API_KEY = "ТОКЕН_IIKO"


async def fetch_orders():
    """Пример получения заказов из iiko"""
    url = f"{BASE_URL}/orders"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("orders", [])
            else:
                return []
