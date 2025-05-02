# bankruptcy.py - API для проверки банкротств (актуальная версия)

from fastapi import APIRouter, Query, HTTPException
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/check-individual", response_model=ApiResponse)
async def check_individual_bankruptcy(
        lastname: str = Query(None, min_length=1, max_length=50, description="Фамилия"),
        firstname: str = Query(None, min_length=1, max_length=50, description="Имя"),
        middlename: str = Query(None, min_length=1, max_length=50, description="Отчество (необязательно)"),
        inn: str = Query(None, min_length=10, max_length=12, regex=r'^\d+$', description="ИНН физического лица"),
        birthdate: str = Query(None, regex=r'^\d{2}\.\d{2}\.\d{4}$', description="Дата рождения в формате DD.MM.YYYY")
) -> ApiResponse:
    """
    Проверка физического лица на банкротство

    Обязательно указать:
    - ИНН или ФИО (фамилию и имя)
    - Для повышения точности при поиске по ФИО рекомендуется указать дату рождения
    """
    # Проверка наличия обязательных параметров
    if not inn and not (lastname and firstname):
        raise HTTPException(
            status_code=400,
            detail="Необходимо указать либо ИНН, либо Фамилию и Имя"
        )

    params = {
        "type": "search",  # Согласно документации API
        "token": config.API_CLOUD_TOKEN,
        "category": "individual"  # Тип поиска - физлицо
    }

    # Добавляем параметры в зависимости от входных данных
    if inn:
        params["in"] = inn  # В API используется 'in' вместо 'inn'

    if lastname and firstname:
        params["query"] = f"{lastname} {firstname}"
        if middlename:
            params["query"] += f" {middlename}"

    if birthdate:
        # Конвертируем дату в формат YYYY-MM-DD
        try:
            day, month, year = birthdate.split('.')
            params["bdate"] = f"{year}-{month}-{day}"
        except:
            logger.warning(f"Неверный формат даты рождения: {birthdate}")

    logger.info(f"Запрос проверки банкротства: {params}")

    try:
        result = await make_api_request("bankrot", params)

        # Обработка ошибок API
        if result.get("status") == "error":
            error_msg = result.get("message", "Неизвестная ошибка API")
            logger.error(f"Ошибка API банкротств: {error_msg}")
            return ApiResponse(
                status="error",
                message=error_msg,
                penalty=0,
                count=0
            )

        # Проверка наличия записей о банкротстве
        cases = result.get("data", {}).get("cases", [])
        active_cases = [case for case in cases if case.get("status") != "завершено"]
        count = len(active_cases)

        # Расчет штрафных баллов (50 за активное дело о банкротстве)
        penalty = 50 if count > 0 else 0

        return ApiResponse(
            status="ok",
            message=f"Найдено {count} активных дел о банкротстве" if count else "Сведений о банкротстве не найдено",
            penalty=penalty,
            count=count,
            data=result.get("data")
        )

    except Exception as e:
        logger.error(f"Ошибка при проверке банкротства: {str(e)}", exc_info=True)
        return ApiResponse(
            status="error",
            message="Внутренняя ошибка сервера при проверке банкротства",
            penalty=0,
            count=0
        )