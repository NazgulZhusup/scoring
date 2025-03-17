import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    KONTOUR_FOCUS_API_KEY = os.getenv("KONTOUR_FOCUS_API_KEY")
    ROSREESTR_API_KEY = os.getenv("ROSREESTR_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")

config = Config()
