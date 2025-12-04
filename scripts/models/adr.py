from dataclasses import dataclass
from datetime import datetime as dt
from enum import Enum
from typing import Optional
from pathlib import Path

class AdrStatus(Enum):
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


@dataclass
class NewAdr:
    slug: str
    date: dt
    status: AdrStatus = AdrStatus.ACCEPTED
    decision: str
    why: list[str]
    _template: str = Path(__file__).parent.parent.parent \
                    / "templates" / "adr.md.mustache"
    stored_in: str = Path(__file__).parent.parent.parent \
                    / "docs" / "adr" / "{slug}.md"
    
@dataclass
class SupersededAdr:
    slug: str
    date: dt
    status: AdrStatus = AdrStatus.SUPERSEDED
    decision: str
    why: list[str]
    supersedes: Path
    _template: str = Path(__file__).parent.parent.parent \
                    / "templates" / "adr.md.mustache"
    stored_in: str = Path(__file__).parent.parent.parent \
                    / "docs" / "adr" / "{slug}.md"