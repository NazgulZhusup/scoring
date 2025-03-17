from fastapi import FastAPI, HTTPException
from app.models import ScoreRequest, ScoreResponse
from app.database import save_application
from app.services.kontur_focus import get_company_data
from app.utils.logger import logger

app = FastAPI(title="Скоринговый сервис", version="1.0")


@app.post("/api/score-calculate", response_model=ScoreResponse)
async def calculate_scoring(request: ScoreRequest):
    try:
        # Сохраняем заявку в базу
        app_id = await save_application(request)

        # Получаем тестовые данные из Контур.Фокус
        company_data = await get_company_data(request.company_inn)

        return {"app_id": app_id, "company_data": company_data}

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")
