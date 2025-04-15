def calculate_score(data, individual_debt, legal_debt, gibdd_data, nalog_data, zalog_data, rosreestr_data, court_cases_penalty):
    score = 0  # Начинаем с 0 баллов
    details = {}

    # 1. Информация о компании
    if data.get("company_exists", False):  # Убедитесь, что поле company_exists существует и логично
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
    if data.get("collateral", False):
        score += 15
        details["collateral"] = 15

    # 4. Репутация владельца (наличие судимости / судебных разбирательств)
    if court_cases_penalty > 0:
        score -= court_cases_penalty
        details["court_cases"] = -court_cases_penalty

    # 5. Судебные дела (наличие долгов по налогу или кредитам)
    if nalog_data and nalog_data.get("status") == "not_found":
        score -= 15
        details["tax_debt"] = -15

    # 6. Просрочки по кредитам
    if data.get("credit_debt", False):  # Нужно точно знать, какое поле здесь
        score -= 20
        details["credit_debt"] = -20

    # 7. Задолженности по физическим и юридическим лицам
    if individual_debt and individual_debt.get("result"):
        debt_count = len(individual_debt["result"])
        penalty = min(20, debt_count * 5)  # Примерный штраф за судебные дела
        score -= penalty
        details["individual_debt"] = -penalty

    if legal_debt and legal_debt.get("result"):
        debt_count = len(legal_debt["result"])
        penalty = min(20, debt_count * 5)
        score -= penalty
        details["legal_debt"] = -penalty

    # 8. Учет состояния автомобиля (ГИБДД)
    if gibdd_data and ("arrest" in gibdd_data or "pledge" in gibdd_data):
        score -= 10  # Штраф за наличие ареста или залога
        details["gibdd_arrest_or_pledge"] = -10

    # 9. Учет залога на транспортное средство (если есть)
    if zalog_data and zalog_data.get("status") == "not_found":
        score -= 15
        details["zalog"] = -15

    # 10. Учет данных из Росреестра (обременения или другие ограничения на недвижимость)
    if rosreestr_data and ("obligation" in rosreestr_data or "restrictions" in rosreestr_data):
        score -= 20  # Снижаем баллы, если есть ограничения или обременения
        details["rosreestr_obligation_or_restrictions"] = -20

    # Ограничиваем максимальное количество баллов
    score = min(90, score)  # Можно установить максимальный порог для баллов
    return score, details
