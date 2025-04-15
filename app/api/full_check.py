from fastapi import APIRouter, Query, HTTPException, Request
from app.api.models import (
    FullCheckResponse,
    PersonData,
    PassportData,
    VehicleData,
    ServiceResult
)
from app.config import config
from .common import make_api_request
import asyncio
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/full-check", response_model=FullCheckResponse)
async def full_check(
        request: Request,
        lastname: str = Query(..., min_length=1, max_length=50),
        firstname: str = Query(..., min_length=1, max_length=50),
        birthdate: str = Query(..., regex=r'^\d{2}\.\d{2}\.\d{4}$'),
        inn: str = Query(..., min_length=10, max_length=12, pattern=r'^\d{10,12}$'),
        passport_series: str = Query(..., min_length=4, max_length=4, pattern=r'^\d+$'),
        passport_number: str = Query(..., min_length=6, max_length=6, pattern=r'^\d+$'),
        region: int = Query(-1, ge=-1),
        vin: Optional[str] = Query(None, min_length=5, max_length=17, pattern=r'^[A-HJ-NPR-Z0-9]{5,17}$')
):
    logger.info(f"Incoming query params: {dict(request.query_params)}")
    """Комплексная проверка по всем базам данных"""
    try:
        # Валидация входных данных
        person = PersonData(
            lastname=lastname,
            firstname=firstname,
            birthdate=birthdate,
            inn=inn,
            passport=PassportData(
                series=passport_series,
                number=passport_number
            ),
            region=region
        )

        # Запуск всех проверок параллельно
        results = await asyncio.gather(
            _check_fssp(person),
            _check_mvd_passport(person.passport),
            _check_mvd_restrictions(person),
            _check_gibdd(vin) if vin else _skip_check("VIN не указан"),
            _check_arbitrage(person),
            _check_bankruptcy(person),
            return_exceptions=True
        )

        # Обработка результатов
        services = {
            "fssp": _process_result(results[0], "ФССП"),
            "mvd_passport": _process_result(results[1], "МВД (паспорт)"),
            "mvd_restrictions": _process_result(results[2], "МВД (запреты)"),
            "gibdd": _process_result(results[3], "ГИБДД"),
            "arbitrage": _process_result(results[4], "Арбитраж"),
            "bankruptcy": _process_result(results[5], "Банкротства")
        }

        # Расчет общего риска
        total_risk = sum(s.penalty for s in services.values() if s.penalty)

        return FullCheckResponse(
            status="ok",
            total_risk=total_risk,
            services=services
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def _check_fssp(person: PersonData) -> dict:
    """Проверка ФССП"""
    params = {
        "type": "physical",
        "lastname": person.lastname,
        "firstname": person.firstname,
        "birthdate": person.birthdate,
        "inn": person.inn,
        "passport_number": f"{person.passport.series}{person.passport.number}",
        "region": person.region,
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("fssp", params)


async def _check_mvd_passport(passport: PassportData) -> dict:
    """Проверка паспорта в МВД"""
    params = {
        "type": "passport",
        "series": passport.series,
        "number": passport.number,
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("mvd", params)


async def _check_gibdd(vin: str) -> dict:
    """Проверка VIN в ГИБДД"""
    params = {
        "type": "gibdd_full",
        "vin": vin,
        "include": "fines,accidents,thefts,restrictions",
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("gibdd", params)


async def _check_mvd_restrictions(person: PersonData) -> dict:
    """Проверка ограничений в МВД"""
    params = {
        "type": "restrictions",
        "inn": person.inn,
        "passport_number": f"{person.passport.series}{person.passport.number}",
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("mvd", params)


async def _check_arbitrage(person: PersonData) -> dict:
    """Проверка арбитражных дел"""
    params = {
        "type": "search",
        "query": f"{person.lastname} {person.firstname}",
        "birthdate": person.birthdate,
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("arbitr", params)


async def _check_bankruptcy(person: PersonData) -> dict:
    """Проверка банкротства"""
    params = {
        "type": "individual",
        "token": config.API_CLOUD_TOKEN
    }
    return await _make_request_with_status("bankrot", params)


def _skip_check(reason: str) -> dict:
    """Заглушка для пропущенных проверок"""
    return {
        "status": "skip",
        "message": reason
    }


def _process_result(result: dict, service_name: str) -> ServiceResult:
    """Обработка результата проверки"""
    # Принудительная установка статуса по умолчанию
    status = result.get("status", "error")

    if isinstance(result, Exception):
        return ServiceResult(
            status="error",
            message=f"{service_name}: {str(result)}",
            penalty=0
        )

    if status == "not_found":
        return ServiceResult(
            status="ok",
            message=f"{service_name}: Данные не найдены",
            penalty=0,
            count=result.get("count", 0),
            data=result.get("data")
        )

    count = result.get("count", 1 if result.get("data") else 0)
    penalty = count * 5  # Базовый расчет штрафных баллов

    return ServiceResult(
        status=status,
        message=result.get("message", f"{service_name}: Найдено {count} записей"),
        penalty=result.get("penalty", penalty),
        count=count,
        data=result.get("data")
    )


async def _make_request_with_status(service_name: str, params: dict) -> dict:
    """
    Выполняет API-запрос и гарантирует наличие поля 'status' в ответе.
    """
    try:
        response = await make_api_request(service_name, params)
        # Добавляем статус "ok", если запрос выполнен успешно
        response['status'] = "ok"
        return response
    except Exception as e:
        # Обработка исключений: возвращаем статус "error"
        return {
            "status": "error",
            "message": f"Ошибка при запросе к {service_name}: {str(e)}"
        }
