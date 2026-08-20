from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL

DIR = Path(__file__).absolute().parent.parent.parent
BOT_DIR = Path(__file__).absolute().parent.parent


class EnvBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        yaml_file="config.yaml"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            YamlConfigSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


class BotSettings(EnvBaseSettings):
    TG_API_KEY: str
    TG_ADMIN_ID: str


class OpenAISettings(EnvBaseSettings):
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"


class DBSettings(EnvBaseSettings):
    DB_PATH: str = "db.db"

    @property
    def database_url(self) -> URL | str:
        return f"sqlite+aiosqlite:///{self.DB_PATH}"


class CacheSettings(EnvBaseSettings):
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASS: str | None = None

    # REDIS_DATABASE: int = 1
    # REDIS_USERNAME: int | None = None
    # REDIS_TTL_STATE: int | None = None
    # REDIS_TTL_DATA: int | None = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASS:
            return f"redis://{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


class ModelDeprecation(BaseSettings):
    warning: bool
    is_deprecated: bool


class Model(BaseSettings):
    id: str
    name: str
    template: Optional[str] = None
    bad_russian: bool = False
    price: int = 0
    deprecation: Optional[ModelDeprecation] = None
    source: str = "bot"
    display_name: Optional[str] = None


class Emojis(BaseSettings):
    system: str


class BotLinks(BaseSettings):
    bot_help_link: str
    bot_donate_link: str


class Prompts(BaseSettings):
    system_bot: str
    system_user: str


class ConfigSettings(EnvBaseSettings):
    models: list[Model]
    default_model_id: str
    instruction_template_path: str
    max_image_width: int
    emojis: Emojis
    links: BotLinks
    prompts: Prompts


class Settings(BotSettings, OpenAISettings, DBSettings, CacheSettings, ConfigSettings):
    DEBUG: bool = False


settings = Settings()


OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "HTTP-Referer": "https://t.me/nedogpt_bot",
    "X-Title": "NedoGPT",
}
TG_BOT_ID: str = settings.TG_API_KEY.split(":")[0]
