# Bytez

Scrapy project for collecting news articles from Indian publishers.

## Development

Install dependencies and run tests from the `bytez/` directory:

```bash
pip install scrapy pytest
pytest
```

Run all publishers in one crawl and export to a single file:

```bash
scrapy crawl all_spiders -O data.json
```

For bounded runs, pass explicit limits — defaults allow up to 1000 articles per TOI scope:

```bash
scrapy crawl toi -a max_total_articles=50 -a min_articles_before_ratio_check=0
scrapy crawl all_spiders -O data.json -a max_total_articles=50 -a min_articles_before_ratio_check=0
```

Run individual spiders:

```bash
scrapy crawl indianexpress -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl toi -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl hindu -a max_total_articles=5 -a min_articles_before_ratio_check=0
```
