from fastapi import APIRouter, Query
from app.api.models import ApiResponse
from app.config import config
from .common import make_api_request

router = APIRouter()


@router.get("/check-passport", response_model=ApiResponse)
async def check_passport(
        series: str = Query(..., min_length=4, max_length=4),
        number: str = Query(..., min_length=6, max_length=6)
) -> ApiResponse:
    params = {
        "type": "passport",
        "series": series,
        "number": number,
        "token": config.API_CLOUD_TOKEN
    }
    return await make_api_request("mvd", params)


@router.get("/check-restrictions", response_model=ApiResponse)
async def check_restrictions(
        inn: str = Query(None, min_length=10, max_length=12),
        passport_number: str = Query(None, min_length=10)
) -> ApiResponse:
    params = {
        "type": "restrictions",
        "token": config.API_CLOUD_TOKEN
    }
    if inn:
        params["inn"] = inn
    if passport_number:
        params["passport_number"] = passport_number

    return await make_api_request("mvd", params)
