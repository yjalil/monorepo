from dataclasses import dataclass
from pathlib import Path


@dataclass
class NewNote:
    slug: str
    explanation: str
    code: str
    language: str
    _template: str = Path(__file__).parent.parent.parent \
                    / "templates" / "note.md.mustache"
    stored_in: str = Path(__file__).parent.parent.parent \
                    / "docs" / "notes" / "{slug}.md"
