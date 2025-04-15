# models.py - Модели данных и исключения

from typing import Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re

# Маппинг HTTP-статусов к строковым статусам сервиса
HTTP_STATUS_TO_SERVICE_STATUS = {
    200: "ok",
    404: "not_found",
    408: "timeout",
    500: "error",
    # Можно добавить другие соответствия при необходимости
}

def normalize_service_status(status: Any) -> str:

    if isinstance(status, int):
        return HTTP_STATUS_TO_SERVICE_STATUS.get(status, "error")
    if isinstance(status, str) and status in {"ok", "error", "not_found", "timeout", "skip"}:
        return status
    return "error"

class ServiceResult(BaseModel):
    """Модель результата отдельного сервиса"""
    status: Literal["ok", "error", "not_found", "timeout", "skip"]
    message: str
    details: Optional[str] = None
    penalty: Optional[int] = 0
    count: Optional[int] = 0
    data: Optional[Dict] = None

    @validator('status', pre=True)
    def validate_status(cls, v):
        # Автоматически нормализуем статус при создании объекта
        return normalize_service_status(v)

class FullCheckResponse(BaseModel):
    """Модель ответа для комплексной проверки"""
    status: Literal["ok", "error"]
    total_risk: int
    services: Dict[str, ServiceResult]
    details: Optional[str] = None

    @validator('status', pre=True)
    def validate_status(cls, v):
        # Гарантируем, что статус всегда строка из допустимых
        if v not in {"ok", "error"}:
            return "error"
        return v

class ApiError(Exception):
    """Кастомное исключение для API"""

    def __init__(self, message: str, status_code: int = 400, details: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class PassportData(BaseModel):
    """Модель данных паспорта"""
    series: str = Field(..., min_length=4, max_length=4, pattern=r'^\d{4}$')
    number: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')

class VehicleData(BaseModel):
    """Модель данных транспортного средства"""
    vin: str = Field(..., min_length=5, max_length=17)
    include: Optional[str] = "fines,accidents,thefts,restrictions"

class PersonData(BaseModel):
    """Модель персональных данных"""
    lastname: str = Field(..., min_length=1)
    firstname: str = Field(..., min_length=1)
    birthdate: str
    inn: str = Field(..., min_length=10, max_length=12, pattern=r'^\d{10,12}$')
    passport: PassportData
    region: int = Field(-1, ge=-1)

    @validator('birthdate')
    def validate_birthdate(cls, v):
        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', v):
            raise ValueError('Дата должна быть в формате ДД.ММ.ГГГГ')
        try:
            day, month, year = map(int, v.split('.'))
            birth_date = datetime(year=year, month=month, day=day)
            if birth_date > datetime.now():
                raise ValueError('Дата рождения не может быть в будущем')
            if year < 1900:
                raise ValueError('Год рождения должен быть не ранее 1900')
        except ValueError:
            raise ValueError('Некорректная дата')
        return v
