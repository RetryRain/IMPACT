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
# Clustering only (ingest / embed / assign)
pip install -e "./clustering[dev]"

# Include synthesis (OpenRouter); required for `synthesize`
pip install -e "./clustering[dev,synthesis]"
```

3. Run migrations:

```bash
cd clustering
alembic upgrade head
```

Migration `002` adds `articles.content_hash` for incremental ingest. Run once against Neon before deploying the new code.

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
| `SYNTHESIS_DATABASE_URL` | placeholder Neon publish DB |
| `SYNTHESIS_PROVIDER` | `deepseek` (or `openrouter`) |
| `DEEPSEEK_API_KEY` | required when provider is `deepseek` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | `deepseek-chat` |
| `OPENROUTER_API_KEY` | required when provider is `openrouter` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | `google/gemini-2.5-flash` |
| `SYNTHESIS_BODY_CHAR_LIMIT` | `800` |
| `SYNTHESIS_TIMEOUT_SECONDS` | `120` |
| `SYNTHESIS_CONCURRENCY` | `3` (parallel LLM calls per run) |
| `SYNTHESIS_LOG_PATH` | `logs/synthesis.jsonl` (JSONL audit log per run) |

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

# Synthesize ready_for_llm clusters (DeepSeek by default)
python -m clustering.cli synthesize --limit 10

# Collapse duplicate published stories already in the feed
python -m clustering.cli collapse-stories
python -m clustering.cli collapse-stories --re-synthesize
```

## Synthesis (DeepSeek or OpenRouter)

After clustering marks story groups `ready_for_llm`, run the synthesis worker against a **separate Neon database**:

1. Install synthesis extras: `pip install -e "./clustering[synthesis]"` (or `[dev,synthesis]` for local dev).
2. Set `SYNTHESIS_DATABASE_URL` and provider credentials in `.env` (see below).
3. Run publish migrations:

```bash
cd clustering
alembic -c alembic_publish.ini upgrade head
```

4. Synthesize:

```bash
python -m clustering.cli synthesize --limit 10
```

Each run appends to `logs/synthesis.jsonl` (or `SYNTHESIS_LOG_PATH`). One JSON object per line:

- **`type: cluster`** — per-cluster outcome (`rewritten`, `dropped`, `failed`, or `skipped_existing`), LLM fields, sources, timing
- **`type: summary`** — run totals and duration (last line of the run)

The worker sends one LLM request per cluster (DeepSeek direct API by default). Irrelevant clusters are dropped (marked `synthesized` in the clustering DB, no publish row). Important clusters are rewritten without bias using all sources, then stored in `synthesized_stories` with:

- LLM fields: `title`, `summary`, `body`, `scope` (verified), `priority` (1–100 editorial score), `slug` (stable SEO URL segment)
- Cloned from representative article: `url`, `source`, `author`, `image`, `tags`, `language`, `published_at`, `scraped_at`
- Provenance: `source_urls`, `sources`
- `synthesized_at` — timestamp when the LLM response was received

### Provider switch

Default is direct DeepSeek (`SYNTHESIS_PROVIDER=deepseek`):

```env
SYNTHESIS_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
```

To use OpenRouter again (one env change):

```env
SYNTHESIS_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-flash
```

The LLM verifies the crawler-assigned scope (`assigned_scope` in the payload) and returns one of `India`, `Tamil Nadu`, or `World`. Priority is scored from Tamil Nadu impact only — not from article count or outlet volume.

### Feed ordering

Order published stories by editorial priority, then recency:

```sql
ORDER BY priority DESC, published_at DESC NULLS LAST
```

Filter by verified scope (e.g. `WHERE scope = 'Tamil Nadu'`).

## Pipeline

1. **Ingest** — Batch-lookup URLs by `content_hash`; skip rewriting unchanged article bodies, but still refresh `scraped_at` on every scrape. Content updates invalidate the article embedding.
2. **Embed** — Only articles missing an embedding row (new or invalidated); does not scan the full table.
3. **Assign** — For each unassigned article (by `published_at`):
   - Find up to **k=5** nearest neighbors within 48h, same `scope`.
   - Join the best neighbor that clears the threshold (0.90 if same `source`, else 0.82).
   - Else create a new cluster.
4. **Event merge** — Before marking clusters ready, fold same-event clusters in the same scope (centroid / pairwise / title overlap). Logs to `logs/event_merge.jsonl`.
5. **Ready** — After cooldown (10 min), mark clusters `ready_for_llm`.

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

## Cloud Run deployment

See [DEPLOY.md](DEPLOY.md) for Cloud Run Jobs setup. For the full end-to-end pipeline (scrape VM + GCS + cron + verify), see [../PIPELINE.md](../PIPELINE.md).
