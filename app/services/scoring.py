def calculate_score(data):
    score = 0  # Начинаем с 0 баллов
    details = {}

    # 1. Информация о компании
    if data.get("company_exists"):
        score += 20
        details["company"] = 20
    if data.get("okved") in ["47.19", "62.01"]:
        score += 10
        details["okved"] = 10

    # 2. Финансовые показатели
    revenue = data.get("revenue", 0)
    requested_loan = data.get("loan_amount", 0)
    if revenue > requested_loan:
        score += 30
        details["revenue_vs_loan"] = 30

    # 3. Наличие залога
    if data.get("collateral"):
        score += 15
        details["collateral"] = 15

    # 4. Репутация владельца
    if data.get("good_credit_history"):
        score += 25
        details["credit_history"] = 25

    # 5. Судебные дела
    court_cases = data.get("court_cases", 0)
    if court_cases > 0:
        penalty = min(20, court_cases * 5)
        score -= penalty
        details["court_cases"] = -penalty

    # 6. Долги по налогам
    if data.get("tax_debt"):
        score -= 15
        details["tax_debt"] = -15

    # 7. Просрочки по кредитам
    if data.get("credit_debt"):
        score -= 20
        details["credit_debt"] = -20

  
    score = min(90, score)
    return score, details
