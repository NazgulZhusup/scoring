import httpx

async def get_company_data(inn: str):
    """
    Временная заглушка для запроса в Контур.Фокус.
    Когда появится API-ключ, заменим на реальный запрос.
    """
    # Симулируем тестовый ответ (пример из документации Контур.Фокус)
    fake_response = {
        "company": {
            "name": "ООО Ромашка",
            "ogrnDate": "2015-06-01",
            "okved": "47.19",
            "region": "Москва",
            "executions": []
        }
    }
    return fake_response
