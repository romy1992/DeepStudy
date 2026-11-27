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
    ai_daily_budget_cents: int = Field(default=0, ge=0, le=100_000)
    weekly_minutes: int | None = Field(default=None, ge=0, le=2400)
    revision: int = Field(default=0, ge=0)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso orario non valido.")
        return value


class StudySessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objective_id: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9]+$")
    mode: Literal["lettura", "esercizio", "quiz"] = "lettura"


class NoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    note_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    base_version: str | None = Field(default=None, max_length=80)
    content: str = Field(min_length=1, max_length=8000)
    objective_id: str | None = Field(default=None, max_length=40)


class AttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    question_version_id: str = Field(min_length=2, max_length=80)
    answer: list[str] = Field(min_length=1, max_length=12)


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=8, pattern=r"^[a-z0-9]+$")
    text: str = Field(min_length=1, max_length=400)


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objective_id: str = Field(min_length=2, max_length=40)
    prompt: str = Field(min_length=8, max_length=2000)
    options: list[QuestionOption] = Field(default_factory=list, max_length=8)
    solution: list[str] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=8, max_length=2000)
    bank: Literal["study", "mock", "flashcard"]
    family: str = Field(min_length=2, max_length=80)
    kind: Literal["single", "multi", "flashcard"]
    origin: Literal["authored", "ai_draft"] = "authored"


class TutorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=3, max_length=2000)
    policy: Literal["off", "local", "cloud"]
    estimate_cents: int = Field(default=0, ge=0, le=100_000)
    session_id: str | None = Field(default=None, max_length=80)


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objective_id: str = Field(min_length=2, max_length=40)
    version_id: str = Field(min_length=2, max_length=80)
    locator: str = Field(min_length=1, max_length=200)
    coverage: str = Field(min_length=1, max_length=200)
    review: Literal["reviewed", "unreviewed"]


class PracticeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    note: str = Field(min_length=8, max_length=2000)


class BlueprintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    source: str = Field(min_length=20, max_length=500)
    question_ids: list[str] = Field(min_length=1, max_length=40)


class MockStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    blueprint_id: str = Field(min_length=2, max_length=80)


class MockAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    question_version_id: str = Field(min_length=2, max_length=80)
    answer: list[str] = Field(min_length=1, max_length=12)


class SyncExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    known_ids: list[str] = Field(default_factory=list, max_length=5000)
    events: list[dict] = Field(default_factory=list, max_length=500)


class ReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=3, max_length=120)
    text: str = Field(min_length=20, max_length=4000)


class LabRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str = Field(min_length=1, max_length=8000)
    timeout_s: int = Field(default=2, ge=1, le=5)
