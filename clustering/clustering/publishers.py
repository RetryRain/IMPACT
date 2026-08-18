from __future__ import annotations

from urllib.parse import urlparse

# Higher rank = preferred for hero images.
_IMAGE_SOURCE_RANK: dict[str, int] = {
    "the hindu": 1,
    "hindu": 1,
    "the indian express": 3,
    "indian express": 3,
    "the new indian express": 3,
    "new indian express": 3,
    "the times of india": 2,
    "times of india": 2,
    "toi": 2,
}

_HOST_RANK: tuple[tuple[str, int], ...] = (
    ("indianexpress.com", 3),
    ("newindianexpress.com", 3),
    ("timesofindia.com", 2),
    ("indiatimes.com", 2),
    ("thehindu.com", 1),
)


def publisher_image_rank(source: str | None, url: str | None = None) -> int:
    if source:
        rank = _IMAGE_SOURCE_RANK.get(source.strip().lower())
        if rank is not None:
            return rank

    if not url:
        return 0

    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return 0

    for pattern, rank in _HOST_RANK:
        if host == pattern or host.endswith(f".{pattern}"):
            return rank
    return 0
