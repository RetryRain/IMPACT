import uuid

import pytest

from clustering.url_id import canonicalize_url, url_to_id


def test_canonicalize_url_strips_fragment_and_tracking_params():
    raw = (
        "HTTPS://Example.COM/article/?utm_source=twitter&fbclid=abc&keep=1#section"
    )
    assert (
        canonicalize_url(raw)
        == "https://example.com/article?keep=1"
    )


def test_canonicalize_url_strips_trailing_slash():
    assert canonicalize_url("https://example.com/foo/") == "https://example.com/foo"


def test_url_to_id_is_stable():
    url = "https://example.com/story"
    first = url_to_id(url)
    second = url_to_id(url + "/")
    third = url_to_id(url + "?utm_campaign=x")
    assert first == second == third
    assert isinstance(first, uuid.UUID)
