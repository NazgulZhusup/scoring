import asyncpg
from app.config import config

async def get_db_connection():
    return await asyncpg.connect(config.DATABASE_URL)

async def save_application(data, score, risk_level):
    conn = await get_db_connection()
    query = """
        INSERT INTO applications (company_exists, okved, revenue, loan_amount, collateral, good_credit_history, score, risk_level)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
    """
    app_id = await conn.fetchval(query, data["company_exists"], data["okved"], data["revenue"], data["loan_amount"], data["collateral"], data["good_credit_history"], score, risk_level)
    await conn.close()
    return app_id
