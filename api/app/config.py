"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_environment(
    env_file: str | Path = DEFAULT_ENV_FILE,
    *,
    override: bool = False,
) -> bool:
    """Load `.env` into `os.environ` for modules that read env directly."""
    return load_dotenv(env_file, override=override)


load_environment()


class Settings(BaseSettings):
    """Settings sourced from `.env` file and environment variables."""

    gemini_api_key: str
    tavily_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Split comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — reads `.env` once per process."""
    return Settings()
