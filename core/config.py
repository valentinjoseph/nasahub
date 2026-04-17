import os
from dotenv import load_dotenv

load_dotenv("infra/.env")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
API_ENABLE_DOCS = env_bool("API_ENABLE_DOCS", False)
API_REQUIRE_AUTH = env_bool("API_REQUIRE_AUTH", False)
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")
VIEWER_ACCESS_TOKEN = os.getenv("VIEWER_ACCESS_TOKEN")
RATE_LIMIT_ENABLED = env_bool("RATE_LIMIT_ENABLED", True)
PUBLIC_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("PUBLIC_RATE_LIMIT_WINDOW_SECONDS", "60"))
PUBLIC_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("PUBLIC_RATE_LIMIT_MAX_REQUESTS", "240"))
ASK_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("ASK_RATE_LIMIT_MAX_REQUESTS", "30"))
NASA_API_KEY = os.getenv("NASA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
BACKUP_ROOT = os.getenv("BACKUP_ROOT", os.path.join(PROJECT_ROOT, "backups", "postgres"))
MONITOR_STATUS_FILE = os.getenv(
    "MONITOR_STATUS_FILE",
    os.path.join(BACKUP_ROOT, "latest_monitor_status.json"),
)

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
