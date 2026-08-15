import { slugify_title, make_story_slug } from "clustering.slug"
import uuid


def test_slugify_title():
    assert slugify_title("Chennai Water Release!") == "chennai-water-release"
    assert slugify_title("") == "story"


def test_make_story_slug():
    story_id = uuid.UUID("a3f21c12-0000-4000-8000-000000000001")
    slug = make_story_slug("Chennai Water Release", story_id)
    assert slug.startswith("chennai-water-release-")
    assert slug.endswith("a3f21c")
