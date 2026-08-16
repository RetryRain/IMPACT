from clustering.event_merge import title_jaccard


def test_title_jaccard_requires_multiple_shared_tokens_for_soft_merge():
    jaccard, shared = title_jaccard(
        "Modi addresses nation on Independence Day",
        "Prime Minister Modi Independence Day speech",
    )
    assert shared >= 2
    assert jaccard > 0.35


def test_title_jaccard_single_shared_token_is_weak():
    _, shared = title_jaccard(
        "Iran conflict escalates in Gulf",
        "Oil prices rise amid Iran tensions",
    )
    assert shared == 1
