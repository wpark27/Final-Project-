"""Pydantic models shared by the calendar data, the crawler agent and the notifier."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["earnings", "rate_decision", "market_report", "election", "summit", "appointment"]
Status = Literal["projected", "confirmed", "reported"]
Category = Literal[
    "pe_sponsor", "credit_sponsor", "bulge_bank", "advisory", "central_bank", "research",
    "us_politics", "uk_politics", "eu_politics", "euro_national",
]


class Result(BaseModel):
    """What the agent pulled from the official source once the event happened."""

    headline: str
    summary: str
    metrics: list[str] = Field(default_factory=list)
    url: str
    published: date | None = None
    detected_at: str | None = None


class Event(BaseModel):
    id: str
    kind: Kind
    entity: str
    ticker: str | None = None
    category: Category
    region: str
    date: date
    title: str
    status: Status = "projected"
    source_url: str
    result: Result | None = None


# ---- structured outputs the LLM agent must return --------------------------------


class ReleaseCheck(BaseModel):
    """Verdict for one expected event, based ONLY on the fetched official page(s)."""

    released: bool = Field(
        description="True only if the official source shows the report/decision is already published."
    )
    confirmed_date: date | None = Field(
        default=None,
        description="If not yet released: the date the official source announces for it, if stated.",
    )
    headline: str | None = None
    summary: str | None = Field(default=None, description="2-3 factual sentences, no speculation.")
    metrics: list[str] = Field(
        default_factory=list,
        description="Key figures exactly as stated, e.g. 'Distributable earnings $1.30/share', 'Fed funds target 3.50-3.75%'.",
    )
    url: str | None = Field(default=None, description="Direct URL of the release/decision.")
    published: date | None = None


class DiscoveredReport(BaseModel):
    entity: str
    title: str
    url: str
    published: date
    summary: str


class DiscoveryResult(BaseModel):
    reports: list[DiscoveredReport] = Field(default_factory=list)
