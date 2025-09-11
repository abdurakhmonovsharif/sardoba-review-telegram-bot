import os
from pydantic import BaseModel

class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPER_ADMINS: list[int] = [
        int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x.strip()
    ]
    APP_ENV: str = os.getenv("APP_ENV", "dev")

settings = Settings()