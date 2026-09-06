from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ────────────────────────────────────────────────────────────────────

class Category(str, Enum):
    technical  = "Technical"
    cultural   = "Cultural"
    sports     = "Sports"
    academic   = "Academic"
    other      = "Other"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip(v: str) -> str:
    return v.strip()


# ── Request schemas ───────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    title:         str      = Field(..., min_length=1, max_length=100)
    description:   str      = Field(..., min_length=1, max_length=500)
    date:          date
    time:          str      = Field(..., pattern=r"^\d{2}:\d{2}$")   # HH:MM
    venue:         str      = Field(..., min_length=1, max_length=120)
    category:      Category = Category.other
    max_attendees: Optional[int] = Field(None, gt=0)

    @field_validator("title", "description", "venue", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return _strip(v)

    @field_validator("title", mode="after")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("title cannot be empty or whitespace")
        return v

    @field_validator("date", mode="after")
    @classmethod
    def date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("date must be today or in the future")
        return v


class EventUpdate(BaseModel):
    """All fields optional — only send what changed."""
    title:         Optional[str]      = Field(None, min_length=1, max_length=100)
    description:   Optional[str]      = Field(None, min_length=1, max_length=500)
    date:          Optional[date]     = None
    time:          Optional[str]      = Field(None, pattern=r"^\d{2}:\d{2}$")
    venue:         Optional[str]      = Field(None, min_length=1, max_length=120)
    category:      Optional[Category] = None
    max_attendees: Optional[int]      = Field(None, gt=0)

    @field_validator("title", "description", "venue", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return _strip(v) if isinstance(v, str) else v

    @field_validator("date", mode="after")
    @classmethod
    def date_not_in_past(cls, v):
        if v and v < date.today():
            raise ValueError("date must be today or in the future")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> EventUpdate:
        values = self.model_dump(exclude_none=True)
        if not values:
            raise ValueError("at least one field must be provided for update")
        return self


# ── Response schema ───────────────────────────────────────────────────────────

class EventOut(BaseModel):
    id:            str
    title:         str
    description:   str
    date:          str          # ISO date string for JSON serialisation
    time:          str
    venue:         str
    category:      str
    max_attendees: Optional[int]
    created_at:    datetime
    updated_at:    datetime

    model_config = {"populate_by_name": True}

    @classmethod
    def from_mongo(cls, doc: dict) -> "EventOut":
        """Convert a raw MongoDB document to EventOut."""
        return cls(
            id            = str(doc["_id"]),
            title         = doc["title"],
            description   = doc["description"],
            date          = str(doc["date"]),
            time          = doc["time"],
            venue         = doc["venue"],
            category      = doc.get("category", "Other"),
            max_attendees = doc.get("max_attendees"),
            created_at    = doc["created_at"],
            updated_at    = doc["updated_at"],
        )


# ── Utility response shapes ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str
    timestamp: datetime


class ReadyResponse(BaseModel):
    ready:     bool
    reason:    Optional[str] = None


class VersionResponse(BaseModel):
    version:        str
    build:          str
    hostname:       str
    environment:    str
    uptime_seconds: float


class LoadResponse(BaseModel):
    status:     str
    duration:   int
    cores_used: int


class DeleteResponse(BaseModel):
    message: str
    id:      str
