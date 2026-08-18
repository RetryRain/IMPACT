from __future__ import annotations

import uuid
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

STRIP_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


def canonicalize_url(url: str) -> str:
    """Normalize a URL so the same article always hashes to the same ID."""
    stripped = url.strip()
    if not stripped:
        raise ValueError("URL must be non-empty")

    parsed = urlparse(stripped)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if not netloc and parsed.path:
        # urlparse treats "example.com/path" as path-only
        reparsed = urlparse(f"https://{stripped}")
        scheme = reparsed.scheme.lower()
        netloc = reparsed.netloc.lower()
        path = reparsed.path or "/"
        query = reparsed.query
        fragment = reparsed.fragment
    else:
        path = parsed.path or "/"
        query = parsed.query
        fragment = parsed.fragment

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_query = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered == "fbclid" or any(
            lowered.startswith(prefix) for prefix in STRIP_QUERY_PREFIXES
        ):
            continue
        filtered_query.append((key, value))

    filtered_query.sort()
    normalized_query = urlencode(filtered_query)

    # Fragments are not sent to servers; strip for stable identity.
    return urlunparse((scheme, netloc, path, "", normalized_query, ""))


def url_to_id(url: str) -> uuid.UUID:
    """Deterministic article ID from a canonical URL."""
    return uuid.uuid5(uuid.NAMESPACE_URL, canonicalize_url(url))
