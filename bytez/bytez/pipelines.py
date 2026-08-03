from urllib.parse import urlsplit, urlunsplit

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class BytezPipeline:
    def __init__(self):
        self.seen_urls = set()

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for duplicate detection."""
        parts = urlsplit(url)

        # Remove query parameters and fragments
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                "",
                "",
            )
        )

    def process_item(self, item):
        adapter = ItemAdapter(item)

        # Drop duplicate articles
        url = adapter.get("url")
        if url:
            normalized_url = self.normalize_url(url)

            if normalized_url in self.seen_urls:
                raise DropItem(f"Duplicate article: {normalized_url}")

            self.seen_urls.add(normalized_url)
            adapter["url"] = normalized_url

        # Clean whitespace without flattening article paragraph breaks.
        for field in (
            "title",
            "summary",
            "author",
            "scope",
        ):
            value = adapter.get(field)
            if isinstance(value, str):
                adapter[field] = " ".join(value.split())

        body = adapter.get("body")
        if isinstance(body, str):
            adapter["body"] = "\n".join(
                " ".join(paragraph.split())
                for paragraph in body.splitlines()
                if paragraph.strip()
            )

        # Remove duplicate/empty tags
        tags = adapter.get("tags")
        if tags:
            adapter["tags"] = list(
                dict.fromkeys(tag.strip() for tag in tags if tag.strip())
            )

        return item
