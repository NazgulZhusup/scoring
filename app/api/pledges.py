# pledges.py - API для проверки залогов

from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

pledges_router = APIRouter()


@pledges_router.get("/check-vehicle", response_model=ApiResponse)
async def check_vehicle_pledge(
        vin: str = Query(..., min_length=5),
        check_type: str = Query("all", description="all|notary|bank")
) -> ApiResponse:
    """Проверка залогов ТС (РЕЕСТР ЗАЛОГОВ)"""
    params = {
        "type": "vehicle",
        "vin": vin,
        "check_type": check_type,
        "token": config.API_CLOUD_TOKEN
    }

    result = await make_api_request("zalog", params)

    if result.get("in_pledge", False):
        return ApiResponse(
            status="ok",
            message="Найдены записи о залоге",
            penalty=40,  # Высокий риск
            count=len(result.get("pledges", [])),
            data=result
        )

    return ApiResponse(
        status="ok",
        message="Залогов не найдено",
        penalty=0,
        count=0,
        data=result
    )