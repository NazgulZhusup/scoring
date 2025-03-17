import httpx
from app.config import config


async def get_company_data(inn: str):
    url = f"https://focus-api.kontur.ru/api3/companies?inn={inn}"
    headers = {"X-API-Key": config.KONTOUR_FOCUS_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Ошибка получения данных"}
