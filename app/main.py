from fastapi import FastAPI
from app.services.kontur_focus import get_company_data
from pydantic import BaseModel

app = FastAPI()


# Определяем модель входных данных
class RequestData(BaseModel):
    company_inn: str


@app.post("/api/score-calculate")
async def process_request(data: RequestData):
    company_data = await get_company_data(data.company_inn)

    return {
        "status": "ok",
        "inn": data.company_inn,
        "company_data": company_data
    }
