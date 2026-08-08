# Bytez Clustering

Semantic duplicate detection and story clustering for scraped Bytez articles. Articles are embedded with Sentence Transformers, stored in PostgreSQL + pgvector, and incrementally grouped into story clusters for downstream LLM synthesis (one rewrite per real-world event).

## Setup

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) must be installed. The CLI needs a running Postgres instance with pgvector.

1. Start Postgres with pgvector:

```bash
docker compose up -d postgres
```

Wait until the container is healthy (`docker compose ps`), then:

2. Install dependencies (from repo root or `clustering/`):

```bash
pip install -e "./clustering[dev]"
```

3. Run migrations:

```bash
cd clustering
alembic upgrade head
```

Environment variables: copy [`.env.example`](.env.example) to `.env` in this directory and edit values. `.env` is gitignored.

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql+psycopg://bytez:bytez@localhost:5432/bytez` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `SIMILARITY_THRESHOLD` | `0.82` |
| `SAME_SOURCE_THRESHOLD` | `0.90` |
| `CLUSTER_TIME_WINDOW_HOURS` | `48` |
| `BODY_CHAR_LIMIT` | `800` |
| `BATCH_SIZE` | `32` |
| `CLUSTER_COOLDOWN_MINUTES` | `10` |

## CLI

```bash
# One-shot batch (prints progress to stderr; JSON summary to stdout)
python -m clustering.cli process --file ../bytez/data.json

# Quiet mode (JSON only)
python -m clustering.cli -q process --file ../bytez/data.json

# Split steps
python -m clustering.cli ingest --file ../bytez/data.json
python -m clustering.cli embed --limit 500
python -m clustering.cli assign --limit 500

# Inspect a cluster (LLM handoff payload)
python -m clustering.cli show-cluster <cluster_id>
```

## Pipeline

1. **Ingest** — Upsert Scrapy `BytezItem` JSON exports on `url`.
2. **Embed** — Build text from `title`, `summary`, and first ~800 chars of `body`; hash to skip unchanged articles.
3. **Assign** — For each unassigned article (by `published_at`):
   - Find nearest neighbor within 48h, same `scope`.
   - If cosine similarity ≥ threshold (0.90 if same `source`, else 0.82) and neighbor has a cluster → join it.
   - Else create a new cluster.
4. **Ready** — After cooldown (10 min), mark clusters `ready_for_llm`.

## LLM handoff contract

Each `ready_for_llm` cluster exposes:

```json
{
  "cluster_id": "...",
  "scope": "India",
  "status": "ready_for_llm",
  "article_count": 3,
  "articles": [
    {
      "source": "The Hindu",
      "title": "...",
      "url": "...",
      "summary": "...",
      "body": "...",
      "published_at": "..."
    }
  ]
}
```

The synthesis worker should consume **clusters**, not raw articles — exactly one LLM call per cluster.

## Threshold calibration

Start strict at **0.82** cosine similarity to reduce false merges. Same-publisher pairs require **0.90** because outlets rarely publish two independent writeups of the identical event with near-identical wording.

Hand-label a few Hindu / TOI / Indian Express pairs as same-event vs different-event and tune `SIMILARITY_THRESHOLD` if needed.

## Tests

```bash
cd clustering
pytest
```

Integration tests against Postgres are skipped unless `DATABASE_URL` is set and reachable.
