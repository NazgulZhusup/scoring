from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.api.full_check import router as full_check_router
from app.api.models import ApiError
from fastapi.exceptions import HTTPException

app = FastAPI(
    title="API для проверки данных",
    description="Полная проверка по всем базам одним запросом",
    version="2.0.0"
)

app.include_router(full_check_router, prefix="/api", tags=["Полная проверка"])

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "required_params": {
                "lastname": "string (1-50 chars)",
                "firstname": "string (1-50 chars)",
                "birthdate": "DD.MM.YYYY",
                "inn": "10-12 digits",
                "passport_series": "4 digits",
                "passport_number": "6 digits"
            }
        }
    )