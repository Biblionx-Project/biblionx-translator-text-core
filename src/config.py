import os
from enum import Enum
from typing import Any

from pydantic import AmqpDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModeEnum(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"
    HOMOLOG = "HOMOLOG"
    TESTING = "TESTING"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=os.path.expanduser(".env"),
        extra="allow",
    )

    MODE: ModeEnum = ModeEnum.DEVELOPMENT

    ENABLE_DL_TRANSLATION: bool = True
    HEALTHCHECK_PORT: int = 80
    TRANSLATOR_QUEUE: str = "translate.to_text"

    AMQP_HOST: str = "localhost"
    AMQP_USER: str = "guest"
    AMQP_PASS: str = "guest"
    AMQP_PORT: str | int = 5672
    AMQP_PREFETCH_COUNT: int = 1
    AMQP_HEART_BEAT: int = 60
    AMQP_URI: AmqpDsn | None = None

    @model_validator(mode="before")
    @classmethod
    def assemble_rabbit_connection(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values

        # Support BIBLIONX_* aliases with fallback
        aliases = {
            "MODE": "BIBLIONX_MODE",
            "ENABLE_DL_TRANSLATION": "BIBLIONX_ENABLE_DL_TRANSLATION",
            "HEALTHCHECK_PORT": "BIBLIONX_HEALTHCHECK_PORT",
            "TRANSLATOR_QUEUE": "BIBLIONX_TRANSLATOR_QUEUE",
            "AMQP_HOST": "BIBLIONX_AMQP_HOST",
            "AMQP_USER": "BIBLIONX_AMQP_USER",
            "AMQP_PASS": "BIBLIONX_AMQP_PASS",
            "AMQP_PORT": "BIBLIONX_AMQP_PORT",
            "AMQP_PREFETCH_COUNT": "BIBLIONX_AMQP_PREFETCH_COUNT",
            "AMQP_HEART_BEAT": "BIBLIONX_AMQP_HEART_BEAT",
        }
        for target, alias in aliases.items():
            if target not in values or values[target] is None:
                if alias in values and values[alias] is not None:
                    values[target] = values[alias]
                elif alias in os.environ and os.environ[alias] is not None:
                    values[target] = os.environ[alias]

        if isinstance(values.get("AMQP_URI"), str):
            return values
        if not all(
            values.get(field)
            for field in ("AMQP_HOST", "AMQP_USER", "AMQP_PASS", "AMQP_PORT")
        ):
            return values

        values["AMQP_URI"] = AmqpDsn.build(
            scheme="amqp",
            host=values.get("AMQP_HOST"),
            password=values.get("AMQP_PASS"),
            username=values.get("AMQP_USER"),
            port=int(values.get("AMQP_PORT")) if values.get("AMQP_PORT") else None,
        )
        return values


settings = Settings()
