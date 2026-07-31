from datetime import UTC, datetime
from typing import ClassVar

import scrapy

from bytez.items import BytezItem


class HinduSpider(scrapy.Spider):
    name: ClassVar[str] = "hindu"
    allowed_domains: ClassVar[tuple[str, ...]] = ("thehindu.com",)

    start_urls: ClassVar[tuple[str, ...]] = (
        "https://www.thehindu.com/news/national/tamil-nadu/",
        "https://www.thehindu.com/news/national/",
        "https://www.thehindu.com/news/international/",
    )

    # Parse each listing page, extract article metadata,
    # and schedule requests to the full article page.
    def parse(self, response):
        articles = response.css("div.element")

        for article in articles:
            url = article.css("h3.title a::attr(href)").get()

            if not url or "/news/" not in url:
                continue

            url = response.urljoin(url)

            title = " ".join(
                t.strip()
                for t in article.css("h3.title a ::text").getall()
                if t.strip()
            )

            scope = article.css(".label a::text").get(default="").strip()

            if not scope:
                if "/news/national/tamil-nadu/" in url:
                    scope = "Tamil Nadu"
                elif "/news/national/" in url:
                    scope = "India"
                elif "/news/international/" in url:
                    scope = "World"

            author = article.css(".author-name a::text").get(default="").strip()

            summary = article.css(".sub-text a::text").get(default="").strip()

            image = (
                article.css(".picture img::attr(data-original)").get()
                or article.css(".picture img::attr(data-src-template)").get()
                or article.css(".picture img::attr(src)").get()
            )

            item = BytezItem(
                title=title,
                url=url,
                scope=scope,
                author=author,
                summary=summary,
                image=image,
                source="The Hindu",
                language="en",
            )

            yield response.follow(
                url,
                callback=self.parse_article,
                meta={"item": item},
            )

        next_page = response.css("li.page-item.next:not(.disabled) a::attr(href)").get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)

    # Parse the full article page and populate the remaining fields.
    def parse_article(self, response):
        item: BytezItem = response.meta["item"]

        paragraphs = response.css(
            "div.articlebodycontent div.schemaDiv[itemprop='articleBody'] p::text"
        ).getall()

        item.body = "\n".join(p.strip() for p in paragraphs if p.strip())

        item.summary = (
            response.css('meta[itemprop="description"]::attr(content)')
            .get(default="")
            .strip()
        )

        item.published_at = response.css(
            'meta[itemprop="datePublished"]::attr(content)'
        ).get()

        raw_keywords = response.css('meta[itemprop="keywords"]::attr(content)').get(
            default=""
        )

        item.tags = [tag.strip() for tag in raw_keywords.split(",") if tag.strip()]

        if not item.author:
            item.author = (
                response.css(".author-name a::text").get(default="").strip()
                or response.css(
                    'span[itemprop="author"] meta[itemprop="name"]::attr(content)'
                )
                .get(default="")
                .strip()
            )

        item.scraped_at = datetime.now(UTC).isoformat()

        yield item
