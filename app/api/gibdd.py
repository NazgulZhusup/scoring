# gibdd.py - API для проверки автомобилей

from fastapi import APIRouter, Query, HTTPException
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request
import logging
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)


def validate_vin(vin: str) -> str:
    """Валидация VIN-номера"""
    vin = vin.upper().strip()
    if not all(c.isalnum() for c in vin):
        raise HTTPException(
            status_code=400,
            detail="VIN должен содержать только буквы и цифры"
        )
    return vin


@router.get("/check", response_model=ApiResponse)
async def check_gibdd(
        vin: str = Query(..., min_length=17, max_length=17,
                         description="VIN-номер транспортного средства (17 символов)"),
        include: str = Query("fines,accidents,thefts,restrictions",
                             description="Какие данные включать в проверку")
) -> ApiResponse:
    try:
        # Валидация и нормализация VIN
        vin = validate_vin(vin)

        params: Dict[str, Any] = {
            "type": "gibdd",
            "vin": vin,
            "check": "all",  # Используем параметр check вместо include
            "token": config.API_CLOUD_TOKEN
        }

        logger.debug(f"Запрос в ГИБДД с параметрами: {params}")

        result = await make_api_request("gibdd", params)
        logger.debug(f"Ответ от ГИБДД: {result}")

        # Обработка различных случаев ответа
        if result.get("status") == "error":
            logger.error(f"Ошибка API ГИБДД: {result.get('message')}")
            return ApiResponse(
                status="error",
                message=result.get("message", "Ошибка при запросе к ГИБДД"),
                penalty=0,
                count=0,
                data=result
            )

        if not result.get("data"):
            return ApiResponse(
                status="ok",
                message="Данные не найдены. Проверьте правильность VIN",
                penalty=0,
                count=0,
                data={"original_response": result}  # Сохраняем оригинальный ответ
            )

        # Расчет штрафных баллов с защитой от None
        fines = result.get("fines", []) or []
        accidents = result.get("accidents", []) or []
        theft_status = result.get("theft_status", {}) or {}
        restrictions = result.get("restrictions", []) or []

        penalties = {
            "fines": len(fines) * 5,
            "accidents": len(accidents) * 10,
            "theft": 20 if theft_status.get("status") == "В угоне" else 0,
            "restrictions": 15 if restrictions else 0
        }
        total_penalty = sum(penalties.values())

        return ApiResponse(
            status="ok",
            message="Полная проверка ГИБДД выполнена",
            penalty=total_penalty,
            count=len(fines) + len(accidents),
            data={
                "result": result,
                "penalty_details": penalties
            }
        )

    except Exception as e:
        logger.error(f"Ошибка при проверке ГИБДД: {str(e)}", exc_info=True)
        return ApiResponse(
            status="error",
            message="Внутренняя ошибка сервера при проверке ГИБДД",
            penalty=0,
            count=0
        )