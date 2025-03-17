import asyncpg
from app.config import config

async def get_db_connection():
    return await asyncpg.connect(config.DATABASE_URL)

async def save_application(request):
    conn = await get_db_connection()
    query = """INSERT INTO applications (company_inn, company_data, loan_data) 
               VALUES ($1, $2, $3) RETURNING id"""
    app_id = await conn.fetchval(query, request.company_inn, request.company_data, request.loan_data.dict())
    await conn.close()
    return app_id
