from clustering.text import build_embedding_text, hash_embedding_text, normalize_whitespace


def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("  hello   world\n\t") == "hello world"


def test_build_embedding_text_truncates_body():
    text = build_embedding_text(
        "Title",
        "Summary",
        "x" * 1200,
        body_char_limit=800,
    )
    assert text.startswith("Title\nSummary\n")
    body_part = text.split("\n", 2)[2]
    assert len(body_part) == 800


def test_build_embedding_text_title_only_fallback():
    text = build_embedding_text("Only title", None, None)
    assert text == "Only title"


def test_hash_embedding_text_is_stable():
    text = build_embedding_text("A", "B", "C")
    assert hash_embedding_text(text) == hash_embedding_text(text)
    assert len(hash_embedding_text(text)) == 64
