from app.services.kontur_focus import get_company_data


async def calculate_score(request):
    company_data = await get_company_data(request.company_inn)

    score = 0
    details = {}

    if company_data:
        score += 50  # Базовые баллы за наличие компании
        details["company_check"] = "Пройдена"

    risk_level = "низкий" if score > 100 else "средний"
    recommendation = "Одобрить" if score > 100 else "Одобрить с повышенной ставкой"

    return {
        "score": score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "details": details
    }
