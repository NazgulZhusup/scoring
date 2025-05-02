from fastapi import APIRouter, Query, HTTPException
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_birthdate(birthdate: str) -> str:
    """Конвертирует дату из DD.MM.YYYY в YYYY-MM-DD"""
    try:
        date_obj = datetime.strptime(birthdate, "%d.%m.%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неправильный формат даты. Используйте DD.MM.YYYY"
        )


@router.get("/check", response_model=ApiResponse)
async def check_fssp(
        lastname: str = Query(..., min_length=1, max_length=50, description="Фамилия"),
        firstname: str = Query(..., min_length=1, max_length=50, description="Имя"),
        birthdate: str = Query(..., regex=r"\d{2}\.\d{2}\.\d{4}", description="Дата рождения в формате DD.MM.YYYY"),
        inn: str = Query(None, min_length=10, max_length=12, description="ИНН (необязательно)"),
        passport_series: str = Query(None, min_length=4, max_length=4, regex=r"^\d+$", description="Серия паспорта"),
        passport_number: str = Query(None, min_length=6, max_length=6, regex=r"^\d+$", description="Номер паспорта"),
        region: int = Query(-1, ge=-1, le=99, description="Код региона (от 0 до 99)")
) -> ApiResponse:
    if not any([inn, passport_series, passport_number]):
        raise HTTPException(
            status_code=400,
            detail="Необходимо указать ИНН или паспортные данные"
        )

    params = {
        "type": "fssp",
        "token": config.API_CLOUD_TOKEN,
        "family": lastname,
        "name": firstname,
        "birthdate": birthdate.replace('.', '-'),
        "in": inn,
        "doc_number": f"{passport_series}{passport_number}",
        "region": region if region != -1 else 77  # Москва по умолчанию
    }

    try:
        result = await make_api_request("fssp", params)

        if "data" not in result:
            result["data"] = []

        return result
    except Exception as e:
        logger.error(f"Ошибка при запросе к ФССП: {str(e)}", exc_info=True)
        return ApiResponse(
            status="error",
            message="Внутренняя ошибка сервера при запросе к ФССП",
            penalty=0,
            count=0
        )