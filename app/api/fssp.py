# fssp.py - API для работы с ФССП

from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

router = APIRouter()


@router.get("/check", response_model=ApiResponse)
async def check_fssp(
        lastname: str = Query(..., min_length=1),
        firstname: str = Query(..., min_length=1),
        birthdate: str = Query(..., regex=r"\d{2}\.\d{2}\.\d{4}"),
        inn: str = Query(..., min_length=10, max_length=12),
        passport_number: str = Query(..., min_length=6),
        region: int = Query(-1, ge=-1)
) -> ApiResponse:
    params = {
        "type": "physical",
        "token": config.API_CLOUD_TOKEN,
        "lastname": lastname,
        "firstname": firstname,
        "birthdate": birthdate,
        "inn": inn,
        "passport_number": passport_number,
        "region": region
    }

    result = await make_api_request("fssp", params)

    if result["status"] == "not_found":
        return ApiResponse(
            status="ok",
            message="Нет задолженностей",
            penalty=0,
            count=0
        )

    if result["status"] != "ok":
        return ApiResponse(**result)

    count = result.get("count", 0)
    penalty = min(20, count * 5)

    return ApiResponse(
        status="ok",
        message=f"Найдено {count} задолженностей",
        penalty=penalty,
        count=count,
        data=result
    )