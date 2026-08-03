# Bytez

Scrapy project for collecting news articles from Indian publishers.

## Development

Install dependencies and run tests from the `bytez/` directory:

```bash
pip install scrapy pytest
pytest
```

Run bounded smoke crawls:

```bash
scrapy crawl indianexpress -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl toi -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl hindu -a max_total_articles=5 -a min_articles_before_ratio_check=0
```
