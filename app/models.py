from pydantic import BaseModel
from typing import List, Optional

class Owner(BaseModel):
    fio: str
    passport: str
    inn: str

class Collateral(BaseModel):
    type: str
    vin: Optional[str] = None

class LoanData(BaseModel):
    amount: int
    term_months: int
    collateral: List[Collateral]

class ScoreRequest(BaseModel):
    company_inn: str
    company_data: dict
    owners: List[Owner]
    loan_data: LoanData
    business_plan: Optional[str] = None

class ScoreResponse(BaseModel):
    app_id: int
    company_data: dict
