from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    locator: str = Field(min_length=1, max_length=4096)
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str = Field(default="", max_length=80)
    theme: Literal["system", "light", "dark"] = "system"
    timezone: str = "Europe/Rome"
    ai_mode: Literal["off"] = "off"
    revision: int = Field(default=0, ge=0)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso orario non valido.")
        return value
