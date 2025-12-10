from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as dt
from enum import Enum
from typing import Any

from pydantic import HttpUrl

from turfoo import settings


@dataclass(frozen=True)
class RSSDetail:
    type: str
    language: str
    base: HttpUrl
    value: str

@dataclass(frozen=True)
class RSSLink:
    rel: str
    type: str
    href: HttpUrl

class RSSFeedType(Enum):
    PROGRAM = settings.conf.TURFOO_PROGRAM_FEED_URL
    NEWS = settings.conf.TURFOO_NEWS_FEED_URL
    RESULTS = settings.conf.TURFOO_RESULTS_FEED_URL
    @property
    def url_str(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class RSSEntry:
    title: str
    title_detail: RSSDetail
    links: list[RSSLink]
    link: HttpUrl
    published: dt
    published_parsed: Any
    id: HttpUrl
    guidislink: bool
    summary: str
    summary_detail: RSSDetail
    published: str

@dataclass(frozen=True)
class Track:
    name: str
    location: str
    surface_type: str

@dataclass(frozen=True)
class Horse:
    name: str
    birth_year: int
    sex: str
    sire: Horse | str | None
    dam: Horse | str | None

@dataclass(frozen=True)
class Jockey:
    name: str

@dataclass(frozen=True)
class Trainer:
    name: str

@dataclass(frozen=True)
class Race:
    date: dt
    track: Track
    race_number: int
    distance_furlongs: float
    surface: str
    track_condition: str
    purse: float
    race_type: str

@dataclass(frozen=True)
class RaceEntry:
    race: Race
    horse: Horse
    jockey: Jockey
    trainer: Trainer
    post_position: int
    morning_line_odds: str
    finish_position: int
    win_payout: float | None
    place_payout: float | None
    show_payout: float | None
