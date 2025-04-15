# gibdd.py - API для проверки автомобилей

from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

router = APIRouter()


@router.get("/check", response_model=ApiResponse)
async def check_gibdd(
        vin: str = Query(..., min_length=5),
        include: str = Query("fines,accidents,thefts,restrictions")
) -> ApiResponse:
    params = {
        "type": "gibdd_full",
        "vin": vin,
        "include": include,
        "token": config.API_CLOUD_TOKEN
    }

    result = await make_api_request("gibdd", params)

    if result["status"] == "not_found":
        return ApiResponse(
            status="ok",
            message="Данные не найдены",
            penalty=0,
            count=0,
            data=result
        )

    if result["status"] != "ok":
        return ApiResponse(**result)

    # Расчет штрафных баллов
    penalties = {
        "fines": len(result.get("fines", [])) * 5,
        "accidents": len(result.get("accidents", [])) * 10,
        "theft": 20 if result.get("theft_status", {}).get("status") == "В угоне" else 0,
        "restrictions": 15 if result.get("restrictions") else 0
    }
    total_penalty = sum(penalties.values())

    return ApiResponse(
        status="ok",
        message="Полная проверка ГИБДД",
        penalty=total_penalty,
        count=sum([
            len(result.get("fines", [])),
            len(result.get("accidents", []))
        ]),
        data=result
    )