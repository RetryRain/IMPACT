from clustering.publishers import publisher_image_rank


def test_publisher_image_rank_ordering():
    assert publisher_image_rank("The Indian Express") > publisher_image_rank(
        "The Times of India"
    )
    assert publisher_image_rank("The Times of India") > publisher_image_rank(
        "The Hindu"
    )
    assert publisher_image_rank(
        None, "https://www.newindianexpress.com/story"
    ) == 3
    assert publisher_image_rank(None, "https://timesofindia.indiatimes.com/x") == 2
    assert publisher_image_rank(None, "https://www.thehindu.com/x") == 1
    assert publisher_image_rank("Unknown Paper", "https://example.com/x") == 0
