# IMPACT

News scraping, semantic clustering, and (future) LLM synthesis for Indian publishers.

## Components

| Folder | Purpose |
|--------|---------|
| [`bytez/`](bytez/) | Scrapy spiders (Hindu, TOI, Indian Express) |
| [`clustering/`](clustering/) | Embed + cluster articles into story groups |
| [`docker-compose.yml`](docker-compose.yml) | Local Postgres + pgvector for development |

## Operations guide

**Start here:** [PIPELINE.md](PIPELINE.md) — full setup for scrape VM, GCS, Cloud Run, Neon, cron, and troubleshooting.

## Quick commands

```bash
# Scrape (from bytez/)
scrapy crawl all_spiders -O data.json

# Cluster locally (from clustering/, Postgres required)
python -m clustering.cli process --file ../bytez/data.json

# Cluster on Cloud Run (after uploading data.json to GCS)
gcloud run jobs execute impact-cluster --region us-central1
```
