# arbitrage.py - API для проверки арбитражных судов

from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

arbitrage_router = APIRouter()


@arbitrage_router.get("/check-arbitr", response_model=ApiResponse)
async def check_arbitr_cases(
        query: str = Query(..., description="ФИО или ИНН"),
        case_type: str = Query("all", description="Тип дела: all|bankruptcy|contract")
) -> ApiResponse:
    """Проверка дел в арбитражных судах (RAS.ARBITR)"""
    params = {
        "type": "search",
        "query": query,
        "case_type": case_type,
        "token": config.API_CLOUD_TOKEN
    }

    result = await make_api_request("arbitr", params)

    if result.get("status") == "not_found":
        return ApiResponse(
            status="ok",
            message="Дела не найдены",
            penalty=0,
            count=0
        )

    if result.get("status") != "ok":
        return ApiResponse(**result)

    cases = result.get("cases", [])
    penalty = min(30, len(cases) * 10)  # 10 баллов за каждое дело

    return ApiResponse(
        status="ok",
        message=f"Найдено {len(cases)} дел",
        penalty=penalty,
        count=len(cases),
        data={"cases": cases}
    )