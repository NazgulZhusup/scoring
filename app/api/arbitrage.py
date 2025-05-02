# arbitrage.py - API для проверки арбитражных судов (актуальная версия)

from fastapi import APIRouter, Query, HTTPException
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request
import logging
from typing import Optional
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


def convert_date_format(date_str: str) -> Optional[str]:
    """Конвертирует дату из DD.MM.YYYY в YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


@router.get("/check-arbitr", response_model=ApiResponse)
async def check_arbitr_cases(
        lastname: str = Query(..., min_length=1, max_length=50, description="Фамилия"),
        firstname: str = Query(..., min_length=1, max_length=50, description="Имя"),
        middlename: str = Query(None, min_length=1, max_length=50, description="Отчество"),
        inn: str = Query(None, min_length=10, max_length=12, description="ИНН"),
        birthdate: str = Query(None, regex=r'^\d{2}\.\d{2}\.\d{4}$', description="Дата рождения в формате DD.MM.YYYY"),
        case_type: str = Query("all", description="Тип дела", regex=r'^(all|bankruptcy|contract)$'),
        region: int = Query(None, description="Код региона (необязательно)")
) -> ApiResponse:
    """
    Проверка дел в арбитражных судах

    Обязательные параметры:
    - Фамилия
    - Имя

    Дополнительные параметры для уточнения поиска:
    - Отчество
    - ИНН (наиболее точный поиск)
    - Дата рождения
    - Регион
    """
    params = {
        "type": "search",
        "token": config.API_CLOUD_TOKEN,
        "query": f"{lastname} {firstname}",
        "case_type": case_type,
        "mode": "extended"  # Расширенный поиск
    }

    # Добавляем необязательные параметры
    if middlename:
        params["query"] += f" {middlename}"

    if inn:
        params["in"] = inn  # В API используется 'in' вместо 'inn'

    if birthdate:
        converted_date = convert_date_format(birthdate)
        if converted_date:
            params["bdate"] = converted_date

    if region is not None:
        params["region"] = region

    logger.info(f"Запрос к арбитражу с параметрами: {params}")

    try:
        result = await make_api_request("arbitr", params)

        # Обработка ошибок API
        if result.get("status") == "error":
            error_msg = result.get("message", "Неизвестная ошибка API")
            logger.error(f"Ошибка API арбитража: {error_msg}")
            return ApiResponse(
                status="error",
                message=error_msg,
                penalty=0,
                count=0
            )

        cases = result.get("data", {}).get("cases", [])

        # Фильтруем только активные дела (не завершенные)
        active_cases = [case for case in cases if case.get("status") != "завершено"]
        count = len(active_cases)

        # Расчет штрафных баллов:
        # - 15 баллов за банкротство
        # - 10 баллов за другие дела
        penalty = 0
        for case in active_cases:
            if case.get("type") == "bankruptcy":
                penalty += 15
            else:
                penalty += 10

        # Максимальный штраф - 100 баллов
        penalty = min(100, penalty)

        return ApiResponse(
            status="ok",
            message=f"Найдено {count} дел (активных)" if count else "Активных дел не найдено",
            penalty=penalty,
            count=count,
            data={"cases": active_cases}  # Возвращаем только активные дела
        )

    except Exception as e:
        logger.error(f"Ошибка при проверке арбитража: {str(e)}", exc_info=True)
        return ApiResponse(
            status="error",
            message="Внутренняя ошибка сервера при проверке арбитража",
            penalty=0,
            count=0
        )