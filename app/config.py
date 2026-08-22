import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from project root so local runs work
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of: 1, 0, true, false, yes, no, on, off")


class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPER_ADMINS: list[int] = [
        int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x.strip()
    ]
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    REVIEW_GROUP_BATCH_ENABLED: bool = _env_bool("REVIEW_GROUP_BATCH_ENABLED", False)
    REVIEW_GROUP_BATCH_SIZE: int = int(os.getenv("REVIEW_GROUP_BATCH_SIZE", "10"))

settings = Settings()

if settings.REVIEW_GROUP_BATCH_SIZE < 1:
    raise ValueError("REVIEW_GROUP_BATCH_SIZE must be greater than 0")
