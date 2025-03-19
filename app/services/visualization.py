import asyncpg
import matplotlib.pyplot as plt
import os
from app.config import config


async def get_db_connection():
    return await asyncpg.connect(config.DATABASE_URL)


async def generate_score_distribution():
    """
    Генерирует график распределения скоринговых баллов.
    """
    conn = await get_db_connection()
    query = "SELECT score FROM applications"
    scores = await conn.fetch(query)
    await conn.close()

    if not scores:
        return None  # Если нет данных, ничего не строим

    scores = [row["score"] for row in scores]

    # Создаём график
    plt.figure(figsize=(8, 5))
    plt.hist(scores, bins=10, color='blue', edgecolor='black', alpha=0.7)
    plt.xlabel("Скоринговый балл")
    plt.ylabel("Частота")
    plt.title("Распределение скоринговых баллов")

    # Сохраняем в файл
    file_path = "score_distribution.png"
    plt.savefig(file_path)
    plt.close()

    return file_path
