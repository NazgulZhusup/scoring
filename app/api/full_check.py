from fastapi import APIRouter, Query, HTTPException, Request
from app.api.models import FullCheckResponse, PersonData, PassportData, VehicleData, ServiceResult, ApiResponse
from app.config import config
from .common import make_api_request
import asyncio
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

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
    try:
        # Валидация данных и форматирование
        formatted_birthdate = birthdate.replace('.', '-')
        person = PersonData(
            lastname=lastname,
            firstname=firstname,
            birthdate=formatted_birthdate,
            inn=inn,
            passport=PassportData(
                series=passport_series,
                number=passport_number
            ),
            region=region if region != -1 else None
        )

        vehicle = VehicleData(vin=vin) if vin else None

        # Выполнение проверок через asyncio
        results = await asyncio.gather(
            _check_fssp(person),  # person — это объект типа PersonData
            _check_mvd_passport(person),  # передаем объект PersonData
            _check_mvd_restrictions(person),  # передаем объект PersonData
            _check_gibdd(vehicle) if vehicle else _skip_check("VIN не указан"),
            _check_arbitrage(person),
            _check_bankruptcy(person),
            return_exceptions=True
        )

        # Обработка полученных результатов от сервисов
        services = {
            "fssp": _process_result(results[0], "ФССП"),
            "mvd_passport": _process_result(results[1], "МВД (паспорт)"),
            "mvd_restrictions": _process_result(results[2], "МВД (запреты)"),
            "gibdd": _process_result(results[3], "ГИБДД"),
            "arbitrage": _process_result(results[4], "Арбитраж"),
            "bankruptcy": _process_result(results[5], "Банкротства")
        }

        # Расчет общего риска
        total_risk = sum(s.penalty for s in services.values() if s and s.penalty)

        return FullCheckResponse(
            status="ok",
            total_risk=total_risk,
            services=services,
            details=None
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Функции для обращения к сервисам API и получения данных

async def _check_fssp(person: PersonData) -> Dict[str, Any]:
    # Устанавливаем значение региона по умолчанию, если оно не передано
    region = person.region if person.region is not None else 77  # Москва по умолчанию

    params = {
        "type": "fssp",
        "family": person.lastname,
        "name": person.firstname,
        "birthdate": person.birthdate,
        "doc_number": f"{person.passport.series}{person.passport.number}",
        "region": str(region),  # Используем значение региона
        "token": config.API_CLOUD_TOKEN
    }

    # Отправка запроса
    try:
        response = await make_api_request("fssp", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API ФССП: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API ФССП")


async def _check_mvd_passport(person: PersonData) -> Dict[str, Any]:
    # Логируем параметры запроса
    logger.debug(f"Параметры запроса для проверки паспорта: {person.passport.series}, {person.passport.number}, {person.birthdate}")

    # Формируем параметры запроса
    params = {
        "type": "passport",
        "ser": person.passport.series,  # Серия паспорта
        "num": person.passport.number,  # Номер паспорта
        "birthdate": person.birthdate,  # Дата рождения из PersonData
        "lastname": person.lastname,    # Фамилия
        "firstname": person.firstname,  # Имя
        "token": config.API_CLOUD_TOKEN
    }

    # Отправка запроса
    try:
        response = await make_api_request("mvd", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API МВД: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API МВД")

async def _check_mvd_restrictions(person: PersonData) -> Dict[str, Any]:
    # Проверяем, что хотя бы один обязательный параметр передан (ИНН или паспортные данные)
    if not person.inn and (not person.passport.series or not person.passport.number):
        return ApiResponse(
            status="error",
            message="МВД (запреты): Необходимо указать ИНН или паспортные данные (серия и номер)",
            penalty=0,
            count=0,
            data=None
        )

    # Формируем параметры запроса
    params = {
        "type": "restrict",  # В API используется 'restrict' для проверки ограничений
        "token": config.API_CLOUD_TOKEN
    }

    if person.inn:
        params["in"] = person.inn  # Передаем ИНН, если оно есть

    if person.passport.series and person.passport.number:
        params["doc_number"] = f"{person.passport.series}{person.passport.number}"  # Передаем паспортные данные

    # Логируем параметры запроса для диагностики
    logger.debug(f"Параметры запроса для проверки ограничений: {params}")

    try:
        response = await make_api_request("mvd", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API МВД (запреты): {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API МВД (запреты)")

async def _check_gibdd(vehicle: VehicleData) -> Dict[str, Any]:
    # Проверяем, что передан VIN-код
    if not vehicle.vin:
        return ApiResponse(
            status="error",
            message="ГИБДД: Необходимо указать VIN-код транспортного средства",
            penalty=0,
            count=0,
            data=None
        )

    # Формируем параметры запроса
    params = {
        "type": "gibdd",  # В API используется 'gibdd' для проверки транспортных средств
        "vin": vehicle.vin,  # VIN транспортного средства
        "check": "all",  # Проверка всех доступных данных (штрафы, ДТП, угон и т.д.)
        "token": config.API_CLOUD_TOKEN  # Используем токен для доступа
    }

    # Логируем параметры запроса для диагностики
    logger.debug(f"Параметры запроса для проверки ГИБДД: {params}")

    try:
        response = await make_api_request("gibdd", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API ГИБДД: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API ГИБДД")

async def _check_arbitrage(person: PersonData) -> Dict[str, Any]:
    # Проверяем, что хотя бы один обязательный параметр передан (ИНН или ФИО)
    if not person.inn and (not person.lastname or not person.firstname):
        return ApiResponse(
            status="error",
            message="Арбитраж: Необходимо указать ИНН или фамилию и имя",
            penalty=0,
            count=0,
            data=None
        )

    # Формируем параметры запроса
    params = {
        "type": "arbitr",  # В API используется 'arbitr' для поиска по арбитражным делам
        "token": config.API_CLOUD_TOKEN
    }

    # Если ИНН передан, добавляем его в параметры
    if person.inn:
        params["in"] = person.inn

    # Если ФИО переданы, добавляем их в параметры
    if person.lastname and person.firstname:
        params["query"] = f"{person.lastname} {person.firstname}"

    # Если дата рождения передана, добавляем ее в параметры
    if person.birthdate:
        params["bdate"] = person.birthdate  # Формат даты должен быть DD.MM.YYYY или YYYY-MM-DD

    # Логируем параметры запроса для диагностики
    logger.debug(f"Параметры запроса для проверки арбитражных дел: {params}")

    try:
        response = await make_api_request("arbitr", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API Арбитраж: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API Арбитраж")

async def _check_bankruptcy(person: PersonData) -> Dict[str, Any]:
    # Проверяем, что хотя бы один обязательный параметр передан (ИНН или ФИО)
    if not person.inn and (not person.lastname or not person.firstname):
        return ApiResponse(
            status="error",
            message="Банкротства: Необходимо указать ИНН или фамилию и имя",
            penalty=0,
            count=0,
            data=None
        )

    # Формируем параметры запроса
    params = {
        "type": "bankrot",  # В API используется 'bankrot' для проверки банкротств
        "token": config.API_CLOUD_TOKEN
    }

    # Если ИНН передан, добавляем его в параметры
    if person.inn:
        params["in"] = person.inn

    # Если ФИО переданы, добавляем их в параметры
    if person.lastname and person.firstname:
        params["query"] = f"{person.lastname} {person.firstname}"

    # Если дата рождения передана, добавляем ее в параметры
    if person.birthdate:
        params["bdate"] = person.birthdate  # Формат даты должен быть DD.MM.YYYY или YYYY-MM-DD

    # Логируем параметры запроса для диагностики
    logger.debug(f"Параметры запроса для проверки банкротства: {params}")

    try:
        response = await make_api_request("bankrot", params)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к API Банкротства: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обращении к API Банкротства")

# Универсальная функция для выполнения запроса к API

async def _make_api_call(service_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.debug(f"Making {service_name} request with params: {params}")
        result = await make_api_request(service_name, params)

        if not isinstance(result, dict):
            raise ValueError(f"Invalid response format from {service_name}")

        # Стандартизация ответов
        if "error" in result:
            result["status"] = "error"
        elif "data" not in result:
            result["status"] = "not_found"
            result["data"] = []
        else:
            result["status"] = "ok"

        return result
    except Exception as e:
        logger.error(f"Error calling {service_name}: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "service": service_name
        }

# Функция для пропуска проверки (например, если нет VIN)

async def _skip_check(reason: str) -> Dict[str, Any]:
    return {
        "status": "skip",
        "message": reason
    }

# Функция для обработки результатов

def _process_result(result: Any, service_name: str) -> ApiResponse:
    """Обработка результатов с улучшенной логикой"""
    # Обработка ошибок
    if isinstance(result, Exception):
        return ApiResponse(
            status="error",
            message=f"{service_name}: {str(result)}",
            penalty=0,
            count=0,
            data=None
        )

    if not isinstance(result, dict):
        return ApiResponse(
            status="error",
            message=f"{service_name}: Invalid response format",
            penalty=0,
            count=0,
            data=None
        )

    # Логирование полученного ответа от API для диагностики
    logger.debug(f"Ответ от API для {service_name}: {result}")

    # Обработка ошибок API
    if result.get("status") == "error":
        error_msg = result.get("message", "Unknown error")
        return ApiResponse(
            status="error",
            message=f"{service_name}: {error_msg}",
            penalty=0,
            count=0,
            data={"original_error": result}
        )

    # Стандартные статусы
    if result.get("status") == "not_found":
        return ApiResponse(
            status="ok",
            message=f"{service_name}: Данные не найдены",
            penalty=0,
            count=0,
            data=result.get("data", {}),
        )

    if result.get("status") == "skip":
        return ApiResponse(
            status="ok",
            message=f"{service_name}: {result.get('message', 'Проверка пропущена')}",
            penalty=0,
            count=0,
            data=None
        )

    # Специфическая обработка для "Паспорт недействителен"
    if service_name == "МВД (паспорт)":
        passport_status = result.get("data", {}).get("status")

        # Логируем статус паспорта
        logger.debug(f"Статус паспорта: {passport_status}")

        # Если статус "invalid", считаем паспорт недействительным
        if passport_status == "invalid":
            return ApiResponse(
                status="ok",
                message="Паспорт недействителен",
                penalty=50,
                count=1,
                data=result.get("data")
            )

        # Если паспорт действителен
        return ApiResponse(
            status="ok",
            message="Паспорт действителен",
            penalty=0,
            count=1,
            data=result.get("data")
        )

    return ApiResponse(
        status="ok",
        message=f"{service_name}: Обработка успешна",
        penalty=0,
        count=1,
        data=result.get("data", {}),
    )

    if service_name == "ФССП":
        cases = result.get("data", {}).get("executions", [])
        count = len(cases)
        penalty = min(20, count * 5)
        return ApiResponse(
            status="ok",
            message=f"Найдено {count} исполнительных производств",
            penalty=penalty,
            count=count,
            data={"cases": cases}
        )

    if service_name == "ГИБДД":
        fines = result.get("fines", [])
        accidents = result.get("accidents", [])
        theft_status = result.get("theft_status", {})
        restrictions = result.get("restrictions", [])

        penalty = (
                len(fines) * 5 +
                len(accidents) * 10 +
                (20 if theft_status.get("status") == "В угоне" else 0) +
                (15 if restrictions else 0)
        )

        return ApiResponse(
            status="ok",
            message="Полная проверка ГИБДД выполнена",
            penalty=penalty,
            count=len(fines) + len(accidents),
            data={"fines": fines, "accidents": accidents, "theft_status": theft_status, "restrictions": restrictions}
        )

    if service_name == "Арбитраж":
        cases = result.get("cases", [])
        count = len(cases)
        penalty = sum(15 if case.get("type") == "bankruptcy" else 10 for case in cases)
        penalty = min(100, penalty)

        return ApiResponse(
            status="ok",
            message=f"Найдено {count} дел (активных)" if count else "Активных дел не найдено",
            penalty=penalty,
            count=count,
            data={"cases": cases}
        )

    if service_name == "Банкротства":
        cases = result.get("cases", [])
        count = len(cases)
        penalty = 50 * count

        return ApiResponse(
            status="ok",
            message=f"Найдено {count} активных дел о банкротстве" if count else "Сведений о банкротстве не найдено",
            penalty=penalty,
            count=count,
            data={"cases": cases}
        )