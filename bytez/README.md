# Bytez

Scrapy project for collecting news articles from Indian publishers.

## Development

Install dependencies and run tests from the `bytez/` directory:

```bash
pip install -r requirements.txt pytest
pytest
```

`brotlicffi` is required so HTML responses compressed with Brotli (`br`) can be decoded. Without it, only API-based sources like Indian Express will scrape successfully when browser `Accept-Encoding` headers are enabled.

## Freshness filter (default: last 24 hours)

By default, only articles with a `published_at` within the past **24 hours** are yielded and exported. Older pages may still be visited during discovery (pagination, related links), but stale items are skipped.

```bash
# Default 24-hour window
scrapy crawl all_spiders -O data.json

# Custom window (12 hours)
scrapy crawl all_spiders -O data.json -a max_published_age_hours=12

# Disable freshness filter (legacy: export all scraped articles)
scrapy crawl all_spiders -O data.json -a max_published_age_hours=0
```

Articles with missing or unparseable `published_at` are excluded (strict policy).

## Crawl commands

Run all publishers in one crawl:

```bash
scrapy crawl all_spiders -O data.json
```

For bounded runs:

```bash
scrapy crawl all_spiders -O data.json -a max_total_articles=50 -a min_articles_before_ratio_check=0
```

Run individual spiders:

```bash
scrapy crawl indianexpress -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl toi -a max_total_articles=5 -a min_articles_before_ratio_check=0
scrapy crawl hindu -a max_total_articles=5 -a min_articles_before_ratio_check=0
```

### Runtime arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `max_published_age_hours` | `24` | Only export articles published within this many hours (`0` disables) |
| `max_total_articles` | `1000` | Per-scope cap on **fresh** articles exported |
| `old_article_max_age_days` | `1` | Crawl-stop heuristic when filter is disabled |
| `max_old_article_ratio` | `0.5` | Stop scope when stale encounters exceed this ratio |
| `min_articles_before_ratio_check` | `200` | Minimum encounters before ratio check applies |
