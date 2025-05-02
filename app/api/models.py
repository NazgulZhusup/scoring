from typing import Dict, Optional, Literal, Any, List, Union
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from enum import Enum
import re

class StatusEnum(str, Enum):
    OK = "ok"
    ERROR = "error"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    SKIP = "skip"

class ApiResponse(BaseModel):
    """Базовая модель ответа API"""
    status: StatusEnum
    message: str
    details: Optional[str] = None
    penalty: Optional[int] = 0
    count: Optional[int] = 0
    data: Optional[Dict[str, Any]] = None

    @model_validator(mode='before')
    def normalize_status(cls, values):
        status_mapping = {
            200: StatusEnum.OK,
            404: StatusEnum.NOT_FOUND,
            408: StatusEnum.TIMEOUT,
            500: StatusEnum.ERROR,
            "ok": StatusEnum.OK,
            "error": StatusEnum.ERROR,
            "not_found": StatusEnum.NOT_FOUND,
            "timeout": StatusEnum.TIMEOUT,
            "skip": StatusEnum.SKIP
        }
        if 'status' in values:
            values['status'] = status_mapping.get(values['status'], StatusEnum.ERROR)
        return values

class FullCheckResponse(BaseModel):
    """Модель ответа для комплексной проверки"""
    status: Literal[StatusEnum.OK, StatusEnum.ERROR] = StatusEnum.OK
    total_risk: int = 0
    services: Dict[str, ApiResponse]
    details: Optional[str] = None

class ApiError(BaseModel):
    """Модель ошибки API"""
    status: Literal[StatusEnum.ERROR] = StatusEnum.ERROR
    message: str
    details: Optional[str] = None
    required_params: Optional[Dict[str, str]] = None

class PassportData(BaseModel):
    """Модель данных паспорта"""
    series: str = Field(..., min_length=4, max_length=4, pattern=r'^\d{4}$')
    number: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')

class PersonData(BaseModel):
    """Модель персональных данных"""
    lastname: str = Field(..., min_length=1, max_length=50)
    firstname: str = Field(..., min_length=1, max_length=50)
    birthdate: str  # Например, 'DD.MM.YYYY'
    inn: str = Field(..., min_length=10, max_length=12)
    passport: PassportData
    region: Optional[int] = None
class VehicleData(BaseModel):
    """Модель данных транспортного средства"""
    vin: str = Field(..., min_length=17, max_length=17)
    include: Optional[str] = "fines,accidents,thefts,restrictions"

class ServiceResult(BaseModel):
    """Модель результата для сервисов"""
    status: str
    message: str
    penalty: int = 0
    count: int = 0
    data: Optional[dict] = None