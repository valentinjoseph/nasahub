import os
from dotenv import load_dotenv

load_dotenv("infra/.env")


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
API_TITLE = os.getenv("API_TITLE", "NasaHub API")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
API_ENABLE_DOCS = env_bool("API_ENABLE_DOCS", True)
API_REQUIRE_AUTH = env_bool("API_REQUIRE_AUTH", False)
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")
NASA_API_KEY = os.getenv("NASA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
