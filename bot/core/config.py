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
    # VK
    VK_API_KEY: str
    VK_GROUP_ID: str
    VK_ADMIN_ID: str

    # TG
    TG_API_KEY: str


class OpenAISettings(EnvBaseSettings):
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"


class DBSettings(EnvBaseSettings):# 
    DB_PATH: str = "db.db"

    @property
    def database_url(self) -> URL | str:
        return f"sqlite+aiosqlite:///{self.DB_PATH}"


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
    ai: str


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
    vk_censor_words: list[str]
    donation_msg_chance: float = Field(ge=0, le=1)
    max_image_width: int
    emojis: Emojis
    links: BotLinks
    prompts: Prompts


class Settings(BotSettings, OpenAISettings, DBSettings, ConfigSettings):
    DEBUG: bool = False


settings = Settings()


OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "HTTP-Referer": "https://vk.com/public205906217",
    "X-Title": "NedoGPT",
}

# TODO: i18n
HELP_MSG: str = (
    f"{settings.emojis.system} Вот все популярные команды:"
    "\n!ai <текст> - отвечает на ваш запрос, используя ваш выбранный муд"
    " (по умолчанию используется обычный ассистент)"
    "\n!муд <имя|описание|инструкции|видимость> [значение] - устанавливает"
    " параметры для вашего муда"
    f"\nВсе остальные команды вы можете найти в репозитории бота: {settings.links.bot_help_link}"
)
DONATION_MSG: str = (
    f"{settings.emojis.system} На данный момент, бот предоставляет бесплатный доступ к моделям"
    " OpenRouter без рекламы. Сами модели не всегда бесплатные, при этом я ничего"
    " не зарабатываю с бота. Если вы хотите, чтобы бот продолжал работать - пожалуйста,"
    f" поддержите его здесь: {settings.links.bot_donate_link}"
)