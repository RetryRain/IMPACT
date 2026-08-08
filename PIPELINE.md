# IMPACT Pipeline — Operations Guide

End-to-end guide for scraping news articles, clustering duplicates, and storing results in Postgres.

## Architecture

```mermaid
flowchart LR
  vm[GCE_VM_e2_micro] -->|scrapy crawl| json[data.json]
  json -->|upload| gcs[GCS_bucket]
  gcs -->|download| job[CloudRunJob_impact_cluster]
  job -->|ingest_embed_assign| neon[(Neon_Postgres_pgvector)]
  neon -->|ready_for_llm| llm[LLM_synthesis_future]
```

| Component | Where | Role |
|-----------|--------|------|
| **Scraper** (`bytez/`) | GCE VM (`e2-micro`) | Crawl Hindu, TOI, Indian Express → `data.json` |
| **Handoff** | GCS | `gs://BUCKET/latest/data.json` |
| **Clustering** (`clustering/`) | Cloud Run Job | Ingest → embed → assign → clusters |
| **Database** | Neon (free) | `articles`, `article_embeddings`, `story_clusters` |

**Why split VM + Cloud Run?** The scrape VM has ~1 GB RAM. Embedding (torch + MiniLM) needs ~2 GB. Scraping alone fits the VM; clustering runs in Cloud Run with 2 GiB.

---

## Your current GCP values (example)

Replace if your setup differs:

| Setting | Value |
|---------|--------|
| GCP project | `stacknursery` |
| Region | `us-central1` |
| GCS bucket | `impact-bytez-riaz123` |
| Cloud Run job | `impact-cluster` |
| Image | `us-central1-docker.pkg.dev/stacknursery/impact/cluster:latest` |
| DB secret | `bytez-database-url` (Secret Manager) |

---

## Part 1 — One-time: Database (Neon)

1. Create a project at [neon.tech](https://neon.tech).
2. Copy the Postgres connection string.
3. Convert to SQLAlchemy format (required):

   ```
   postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require
   ```

   **Important:** No trailing spaces in the URL (causes `invalid sslmode value: "require "`).

4. On your laptop, from `clustering/`:

   ```bash
   cp .env.example .env
   # Edit .env → set DATABASE_URL to Neon URL
   pip install -e .
   alembic upgrade head
   ```

5. Confirm tables exist in Neon SQL editor:

   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public';
   ```

   Expected: `articles`, `article_embeddings`, `story_clusters`, `alembic_version`.

---

## Part 2 — One-time: GCP setup

### Install tools

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- Login: `gcloud auth login`

### PowerShell variables

```powershell
$env:PROJECT_ID = "stacknursery"
$env:REGION = "us-central1"
$env:BUCKET = "impact-bytez-riaz123"

gcloud config set project $env:PROJECT_ID
```

### Enable APIs

```powershell
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com storage.googleapis.com
```

### Artifact Registry

```powershell
gcloud artifacts repositories create impact --repository-format=docker --location=$env:REGION
```

### GCS bucket

```powershell
gcloud storage buckets create gs://$env:BUCKET --location=$env:REGION
```

### Database secret (no trailing newline/spaces)

```powershell
# Use echo -n or a file — never add extra spaces
$url = "postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require"
[System.IO.File]::WriteAllText("$env:TEMP\dburl.txt", $url.Trim())
gcloud secrets create bytez-database-url --data-file="$env:TEMP\dburl.txt"
Remove-Item "$env:TEMP\dburl.txt"
```

### IAM for Cloud Run

```powershell
$env:PROJECT_NUMBER = gcloud projects describe $env:PROJECT_ID --format="value(projectNumber)"
$env:SA = "$($env:PROJECT_NUMBER)-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding bytez-database-url `
  --member="serviceAccount:$($env:SA)" `
  --role="roles/secretmanager.secretAccessor"

gcloud storage buckets add-iam-policy-binding gs://$env:BUCKET `
  --member="serviceAccount:$($env:SA)" `
  --role="roles/storage.objectViewer"
```

---

## Part 3 — Build & deploy clustering image

From **repo root** (`IMPACT/`):

```powershell
gcloud builds submit --config cloudbuild.cluster.yaml .
```

Local test (optional):

```powershell
cd clustering
docker build -t impact-cluster:local .
docker run --rm --env-file .env -e DATA_FILE=/tmp/data.json -v "${PWD}/../bytez/data.json:/tmp/data.json:ro" impact-cluster:local
```

---

## Part 4 — Create Cloud Run Job

**Do not set `--command` or `--args`.** The image entrypoint is `python -m clustering.job_entry`.

```powershell
gcloud run jobs create impact-cluster `
  --image "$env:REGION-docker.pkg.dev/$env:PROJECT_ID/impact/cluster:latest" `
  --region $env:REGION `
  --memory 2Gi `
  --cpu 1 `
  --task-timeout 3600 `
  --max-retries 1 `
  --set-secrets=DATABASE_URL=bytez-database-url:latest `
  --set-env-vars="GCS_URI=gs://$env:BUCKET/latest/data.json,RUN_MIGRATIONS=false"
```

If you previously set a custom command, recreate the job or clear overrides:

```powershell
gcloud run jobs update impact-cluster --region $env:REGION --command="" --args=""
```

### Job environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GCS_URI` | (required) | `gs://bucket/latest/data.json` |
| `DATABASE_URL` | from secret | Neon connection string |
| `DATA_FILE` | `/tmp/data.json` | Local path after GCS download |
| `RUN_MIGRATIONS` | `false` | Set `true` to run Alembic on each job |
| `FORCE_READY` | `false` | Set `true` to mark all clusters `ready_for_llm` |
| `PROCESS_LIMIT` | — | Limit articles per step |
| `QUIET` | `false` | Suppress progress logs |

---

## Part 5 — Scrape VM setup

### VM specs

- **Machine:** `e2-micro` (free tier, `us-central1`)
- **OS:** Ubuntu 22.04
- **Python:** 3.10+ (use `timezone.utc`, not `datetime.UTC`)

### Install on VM

```bash
sudo apt update && sudo apt install -y git python3 python3-pip python3-venv

cd ~
git clone <your-repo-url> Bytez   # or scp the bytez folder
cd Bytez/bytez
python3 -m venv .venv
source .venv/bin/activate
pip install scrapy
```

### Test scrape

```bash
scrapy crawl all_spiders -O data.json -a max_total_articles=10 -a min_articles_before_ratio_check=0
```

### Cron (scrape 4× daily)

```cron
30 1,5,10,14 * * * cd /home/rain_reactor/Bytez/bytez && TS=$(date +\%Y\%m\%d-\%H\%M) && /home/rain_reactor/Bytez/bytez/.venv/bin/scrapy crawl all_spiders -O /home/rain_reactor/Bytez/bytez/data.json >> /home/rain_reactor/Bytez/bytez/logs/crawl_reports.log 2>&1 && cp /home/rain_reactor/Bytez/bytez/data.json /home/rain_reactor/Bytez/bytez/history/data-$TS.json
```

Create log/history dirs: `mkdir -p logs history`

---

## Part 6 — Daily pipeline (after each scrape)

### Step A — Upload to GCS (on VM or laptop)

```bash
gcloud storage cp /home/rain_reactor/Bytez/bytez/data.json gs://impact-bytez-riaz123/latest/data.json
```

VM needs `gcloud` auth with a service account that has **Storage Object Creator** on the bucket.

### Step B — Run clustering job

```powershell
gcloud run jobs execute impact-cluster --region us-central1
```

Or async:

```powershell
gcloud run jobs execute impact-cluster --region us-central1 --async
```

### Step C — Check logs

```powershell
gcloud run jobs executions list --job impact-cluster --region us-central1 --limit 3

gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=impact-cluster" --limit 30 --format="value(textPayload)"
```

Success looks like:

```
Downloading gs://impact-bytez-riaz123/latest/data.json -> /tmp/data.json
==> Ingest
==> Embed
==> Assign
Done.
Container called exit(0).
```

### Optional — automate with Cloud Scheduler

Run clustering 20 min after scrape (`:30` scrape → `:50` cluster):

```bash
gcloud scheduler jobs create http impact-cluster-trigger \
  --location us-central1 \
  --schedule "50 1,5,10,14 * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/impact-cluster:run" \
  --http-method POST \
  --oauth-service-account-email SERVICE_ACCOUNT
```

---

## Part 7 — Verify & inspect data

### SQL (Neon console or PostgreSQL extension)

```sql
-- Article count
SELECT COUNT(*) FROM articles;

-- Cluster status breakdown
SELECT status, COUNT(*) FROM story_clusters GROUP BY status;

-- Duplicate groups (clusters with 2+ articles)
SELECT
    a.cluster_id,
    a.source,
    a.title,
    a.published_at
FROM articles a
JOIN (
    SELECT cluster_id
    FROM articles
    WHERE cluster_id IS NOT NULL
    GROUP BY cluster_id
    HAVING COUNT(*) > 1
) c ON a.cluster_id = c.cluster_id
ORDER BY a.cluster_id, a.published_at DESC;
```

### LLM handoff preview (local)

```bash
cd clustering
python -m clustering.cli show-cluster <cluster-uuid>
```

---

## How duplicates are handled

| Layer | Behavior |
|-------|----------|
| **Single crawl** | `BytezPipeline` drops duplicate URLs within one run |
| **Across cron runs** | Same URLs re-scraped (normal — feeds still list recent articles) |
| **Postgres** | `ingest` **upserts on `url`** — no duplicate rows; updates existing articles |
| **Clustering** | Groups semantically similar articles into `story_clusters` |

---

## Cluster statuses

| Status | Meaning |
|--------|---------|
| `open` | Cluster active; may receive new articles |
| `ready_for_llm` | Cooldown passed (10 min); ready for synthesis worker |
| `synthesized` | Reserved for future LLM stage |

---

## Updating after code changes

```powershell
# Rebuild image
gcloud builds submit --config cloudbuild.cluster.yaml .

# Point job at new image (if tag unchanged, job picks up latest on next run)
gcloud run jobs update impact-cluster `
  --image "$env:REGION-docker.pkg.dev/$env:PROJECT_ID/impact/cluster:latest" `
  --region $env:REGION
```

For clustering config changes only (thresholds), update env vars on the job — no rebuild needed.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|--------|-----|
| `invalid choice: 'clustering'` | Wrong CLI argv or old image | Rebuild image; don't override job command |
| `No module named 'clustering'` | Custom `--command` on job | Recreate job without `--command`/`--args` |
| `invalid sslmode value: "require "` | Trailing space in `DATABASE_URL` secret | `gcloud secrets versions add` with trimmed URL |
| `relation "articles" does not exist` | Migrations not run | `alembic upgrade head` against Neon |
| GCS download fails | IAM | Grant `storage.objectViewer` to compute SA |
| Job OOM | Memory too low | Use `--memory 2Gi` minimum |
| Re-scrape feels duplicate | Expected | DB upserts; check `created` vs `updated` in ingest stats |

### Recreate job cleanly

```powershell
gcloud run jobs delete impact-cluster --region us-central1 --quiet
# Then run create command from Part 4 (no --command/--args)
```

---

## Local development

| Task | Command |
|------|---------|
| Start local Postgres | `docker compose up -d postgres` (repo root) |
| Migrate | `cd clustering && alembic upgrade head` |
| Full pipeline | `python -m clustering.cli process --file ../bytez/data.json` |
| Tests | `cd clustering && pytest -m "not integration"` |

---

## Free tier checklist

- [ ] `e2-micro` VM in `us-central1` / `us-east1` / `us-west1`
- [ ] Neon free Postgres (not Cloud SQL)
- [ ] Cloud Run Job ~4 runs/day, 2 GiB, ~3–10 min each
- [ ] GCS bucket for small JSON files
- [ ] One image in Artifact Registry; prune old tags if needed

---

## Related docs

- [bytez/README.md](bytez/README.md) — scraper commands and spider args
- [clustering/README.md](clustering/README.md) — clustering CLI and config
- [clustering/DEPLOY.md](clustering/DEPLOY.md) — Cloud Run deploy reference (technical)

---

## Next stage (not built yet)

**LLM synthesis** — consume `ready_for_llm` clusters via `show-cluster` JSON payload; one LLM call per cluster. See [clustering/README.md](clustering/README.md#llm-handoff-contract).
