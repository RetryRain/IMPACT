from __future__ import annotations

from unittest.mock import MagicMock

from bytez.spiders.all_spiders import AllSpidersSpider
from bytez.spiders.hindu import HinduSpider
from bytez.spiders.indianexpress import IndianExpressSpider
from bytez.spiders.toi import ToiSpider


def make_spider(**kwargs) -> AllSpidersSpider:
    crawler = MagicMock()
    crawler.stats = MagicMock()
    return AllSpidersSpider.from_crawler(crawler, **kwargs)


class TestAllSpidersSpider:
    def test_registers_child_spiders(self):
        spider = make_spider()
        child_types = {type(child) for child in spider._children}
        assert child_types == {
            IndianExpressSpider,
            ToiSpider,
            HinduSpider,
        }

    def test_children_do_not_close_crawl_when_scopes_finish(self):
        spider = make_spider()
        for child in spider._children:
            assert child.tracker.close_on_all_scopes is False

    def test_start_yields_requests_from_every_child(self):
        spider = make_spider()

        async def collect():
            return [request.url async for request in spider.start()]

        import asyncio

        urls = asyncio.run(collect())
        assert any("newindianexpress.com" in url for url in urls)
        assert any("indiatimes.com" in url for url in urls)
        assert any("thehindu.com" in url for url in urls)
