from dataclasses import dataclass, field


@dataclass
class BytezItem:
    title: str | None = None
    url: str | None = None
    scope: str | None = None
    author: str | None = None
    summary: str | None = None
    image: str | None = None

    # Fields to be populated after visiting the article page
    published_at: str | None = None
    body: str | None = None
    tags: list[str] = field(default_factory=list)

    # Metadata
    source: str | None = None
    language: str | None = None
    scraped_at: str | None = None
