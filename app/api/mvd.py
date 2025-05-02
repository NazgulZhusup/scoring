from fastapi import APIRouter, Query, HTTPException
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/check-passport", response_model=ApiResponse)
async def check_passport(
        series: str = Query(..., min_length=4, max_length=4, regex=r'^\d+$', description="Серия паспорта (4 цифры)"),
        number: str = Query(..., min_length=6, max_length=6, regex=r'^\d+$', description="Номер паспорта (6 цифр)")
) -> ApiResponse:
    """
    Проверка паспорта в базе МВД
    """
    params = {
        "type": "passport",
        "token": config.API_CLOUD_TOKEN,
        "ser": series,
        "num": number
    }

    try:
        result = await make_api_request("mvd", params)

        if result.get("status") == "error":
            logger.error(f"Ошибка МВД API: {result.get('message', 'Неизвестная ошибка')}")
            return ApiResponse(
                status="error",
                message=result.get("message", "Ошибка при проверке паспорта"),
                penalty=50 if result.get("data", {}).get("status") == "invalid" else 0,
                count=0
            )

        passport_status = result.get("data", {}).get("status", "not_found")

        return result
    except Exception as e:
        logger.error(f"Ошибка при проверке паспорта: {str(e)}", exc_info=True)
        return ApiResponse(
            status="error",
            message="Внутренняя ошибка сервера при проверке паспорта",
            penalty=0,
            count=0
        )