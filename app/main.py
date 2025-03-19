from fastapi import FastAPI
from pydantic import BaseModel
from app.services.scoring import calculate_score
from app.database import save_application
from fastapi.responses import FileResponse
from app.services.excel_export import generate_excel
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from app.services.visualization import generate_score_distribution

app = FastAPI()

class RequestData(BaseModel):
    company_exists: bool
    okved: str = Field(..., min_length=4, max_length=10)
    revenue: int = Field(..., gt=0, description="Выручка должна быть больше 0")
    loan_amount: int = Field(..., ge=0, description="Сумма займа не может быть отрицательной")
    collateral: bool
    good_credit_history: bool
    court_cases: int = Field(..., ge=0, description="Количество судебных дел не может быть отрицательным")  # Новое поле
    tax_debt: bool  # Долги по налогам
    credit_debt: bool  # Просрочки по кредитам

@app.post("/api/score-calculate")
async def process_request(data: RequestData):
    score, details = calculate_score(data.dict())
    risk_level = "низкий" if score > 50 else "средний" if score > 30 else "высокий"

    # Сохраняем в базу
    app_id = await save_application(data.dict(), score, risk_level)

    return {
        "status": "ok",
        "app_id": app_id,
        "score": score,
        "risk_level": risk_level,
        "details": details
    }


@app.get("/api/export-excel/{app_id}")
async def export_excel(app_id: int):
    file_path = await generate_excel(app_id)
    if not file_path:
        return {"error": "Заявка не найдена"}

    return FileResponse(file_path, filename=f"application_{app_id}.xlsx")


@app.get("/api/score-distribution")
async def get_score_distribution():
    file_path = await generate_score_distribution()
    if not file_path:
        return {"error": "Нет данных для анализа"}

    return FileResponse(file_path, filename="score_distribution.png")


