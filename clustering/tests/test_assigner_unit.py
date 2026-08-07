from types import SimpleNamespace

from clustering.assigner import _effective_threshold


def test_effective_threshold_same_source_is_stricter():
    article = SimpleNamespace(source="The Hindu")
    neighbor = SimpleNamespace(source="The Hindu")
    assert _effective_threshold(article, neighbor, 0.85) == 0.90


def test_effective_threshold_cross_source_uses_default():
    article = SimpleNamespace(source="The Hindu")
    neighbor = SimpleNamespace(source="Times of India")
    assert _effective_threshold(article, neighbor, 0.85) == 0.82
