# bankruptcy.py - API для проверки банкротств

from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

bankruptcy_router = APIRouter()


@bankruptcy_router.get("/check-individual", response_model=ApiResponse)
async def check_individual_bankruptcy(
        inn: str = Query(None, min_length=10, max_length=12),
        fullname: str = Query(None)
) -> ApiResponse:
    """Проверка банкротства физлица (BANKROT)"""
    if not inn and not fullname:
        return ApiResponse(
            status="error",
            message="Укажите ИНН или ФИО"
        )

    params = {
        "type": "individual",
        "token": config.API_CLOUD_TOKEN
    }
    if inn:
        params["inn"] = inn
    if fullname:
        params["fullname"] = fullname

    result = await make_api_request("bankrot", params)

    if result.get("is_bankrupt", False):
        return ApiResponse(
            status="ok",
            message="Найдены сведения о банкротстве",
            penalty=50,  # Высокий риск
            count=1,
            data=result
        )

    return ApiResponse(
        status="ok",
        message="Сведений о банкротстве не найдено",
        penalty=0,
        count=0,
        data=result
    )