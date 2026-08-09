# Deploy clustering to Google Cloud Run Jobs

Batch pipeline: download `data.json` from GCS (optional) → ingest → embed → assign → Postgres.

**Prerequisites:** GCP project with billing, [Neon](https://neon.tech) (or other) Postgres with pgvector, GCS bucket for scrape output.

## Architecture

```
Scrape VM  --upload-->  GCS (gs://BUCKET/latest/data.json)
                              |
                              v
                    Cloud Run Job (impact-cluster)
                              |
                              v
                         Neon Postgres
```

## 1. One-time: Neon database

1. Create a Neon project and enable **pgvector** (`CREATE EXTENSION vector;` — Alembic does this).
2. Copy the connection string and convert to SQLAlchemy format:

   ```
   postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require
   ```

3. From your laptop:

   ```bash
   cd clustering
   # set DATABASE_URL in .env to Neon URL
   alembic upgrade head
   ```

## 2. One-time: GCP setup

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export BUCKET=impact-bytez-runs   # must be globally unique

gcloud config set project $PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com
```

Create Artifact Registry repo:

```bash
gcloud artifacts repositories create impact \
  --repository-format=docker \
  --location=$REGION
```

Create GCS bucket:

```bash
gcloud storage buckets create gs://$BUCKET --location=$REGION
```

Store database URL in Secret Manager:

```bash
echo -n "postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require" | \
  gcloud secrets create bytez-database-url --data-file=-
```

Grant the default compute service account access to the secret and bucket:

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com

gcloud secrets add-iam-policy-binding bytez-database-url \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:${SA}" \
  --role="roles/storage.objectViewer"
```

## 3. Build and push the image

From the **repo root**:

```bash
gcloud builds submit --config cloudbuild.cluster.yaml .
```

Or build locally and push:

```bash
cd clustering
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/impact/cluster:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/impact/cluster:latest
```

## 4. Create the Cloud Run Job

```bash
gcloud run jobs create impact-cluster \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/impact/cluster:latest \
  --region $REGION \
  --memory 2Gi \
  --cpu 1 \
  --task-timeout 3600 \
  --max-retries 1 \
  --set-secrets=DATABASE_URL=bytez-database-url:latest \
  --set-env-vars="GCS_URI=gs://${BUCKET}/latest/data.json,RUN_MIGRATIONS=false"
```

Do **not** set a custom container command or args on the job. The image entrypoint is `python -m clustering.job_entry`. If you previously set `bytez-cluster` or `python -m clustering.cli process`, clear overrides:

```bash
gcloud run jobs update impact-cluster --region $REGION \
  --command="" --args=""
```

Optional env vars:

| Variable | Purpose |
|----------|---------|
| `GCS_URI` | `gs://bucket/path/data.json` to download before process |
| `DATA_FILE` | Local path after download (default `/tmp/data.json`) |
| `RUN_MIGRATIONS` | `true` to run `alembic upgrade head` on each job |
| `FORCE_READY` | `true` → `--force-ready` on assign |
| `PROCESS_LIMIT` | Limit articles processed per step |
| `QUIET` | `true` → suppress progress logs |

Run manually:

```bash
gcloud run jobs execute impact-cluster --region $REGION
```

View logs:

```bash
gcloud run jobs executions list --job impact-cluster --region $REGION
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="impact-cluster"' --limit 30 --format json
```

## 5. Scrape VM: upload after crawl

After your cron scrape, upload to GCS:

```bash
gcloud storage cp /home/rain_reactor/Bytez/bytez/data.json gs://${BUCKET}/latest/data.json
```

Install `gcloud` on the VM and authenticate with a service account that has `storage.objectCreator` on the bucket.

Trigger the job (optional, from VM):

```bash
gcloud run jobs execute impact-cluster --region us-central1 --async
```

## 6. Schedule with Cloud Scheduler (optional)

Run clustering 20 minutes after scrape (scrape at :30, cluster at :50):

```bash
gcloud scheduler jobs create http impact-cluster-trigger \
  --location $REGION \
  --schedule "50 1,5,10,14 * * *" \
  --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/impact-cluster:run" \
  --http-method POST \
  --oauth-service-account-email ${SA}
```

## 7. Verify

```sql
SELECT COUNT(*) FROM articles;
SELECT status, COUNT(*) FROM story_clusters GROUP BY status;
```

## Free tier notes

- Cloud Run Jobs: free tier includes substantial monthly CPU/memory seconds; ~4 runs/day × ~10–15 min at 2 GiB usually stays near $0.
- The embedding model (`all-MiniLM-L6-v2`, ~90 MB) is **downloaded on first use** from Hugging Face and cached under `HF_HOME`. First run after a cold start adds ~1–2 minutes; later runs in the same container reuse the cache.
- Use **2 GiB** memory, **1 vCPU** — enough for MiniLM on CPU.
- Artifact Registry: keep one image tag; delete old images if storage exceeds free 0.5 GB.

## Image size

The Dockerfile uses a **multi-stage build** so compiler tooling (`build-essential`, ~200 MB) and pip caches stay out of the pushed image. The runtime image contains only Python slim, installed wheels (PyTorch CPU, sentence-transformers, etc.), and Alembic migration files.

**Typical sizes** (Artifact Registry compressed):

| Variant | Approx. size |
|---------|----------------|
| Old single-stage + baked model | ~600–650 MB |
| Multi-stage, model downloaded at runtime | ~400–500 MB |

### Build locally and check size

```bash
cd clustering
docker build -t impact-cluster:local .

# Uncompressed image size
docker image ls impact-cluster:local

# Approximate compressed push size (what Artifact Registry bills)
docker save impact-cluster:local | wc -c
# Windows PowerShell:
# (docker save impact-cluster:local -o nul) 2>$null; use `docker buildx imagetools inspect` if using buildx
```

On Linux/macOS, `docker history impact-cluster:local --human` shows which layers dominate.

### Push a smaller image

```bash
export REGION=us-central1
export PROJECT_ID=your-gcp-project

docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/impact/cluster:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/impact/cluster:latest

gcloud run jobs update impact-cluster \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/impact/cluster:latest \
  --region $REGION
```

Or via Cloud Build:

```bash
gcloud builds submit --config cloudbuild.cluster.yaml .
```

### Optional further reductions (not applied by default)

| Change | Savings | Trade-off |
|--------|---------|-----------|
| Multi-stage build (already on) | ~150–250 MB | None |
| Drop baked model (already on) | ~80–90 MB | First embed step downloads model |
| Pin `torch` CPU wheel only in `pyproject.toml` | Small | Must not install CUDA torch by mistake |
| `docker build --squash` (experimental) | Variable | Loses layer cache; harder to debug |
| ONNX / lighter runtime instead of PyTorch | Large | Code change; out of scope today |

Do **not** remove PyTorch or sentence-transformers — they are required for embeddings.

## Local test of the container

```bash
cd clustering
docker build -t impact-cluster:local .

docker run --rm \
  -e DATABASE_URL="postgresql+psycopg://..." \
  -e GCS_URI="" \
  -v "$(pwd)/../bytez/data.json:/tmp/data.json:ro" \
  -e DATA_FILE=/tmp/data.json \
  impact-cluster:local
```

Or mount file only (skip GCS):

```bash
docker run --rm \
  --env-file .env \
  -v /path/to/data.json:/tmp/data.json:ro \
  -e DATA_FILE=/tmp/data.json \
  impact-cluster:local
```

## Update after code changes

```bash
gcloud builds submit --config cloudbuild.cluster.yaml .

gcloud run jobs update impact-cluster \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/impact/cluster:latest \
  --region $REGION
```

## Troubleshooting

| Log error | Fix |
|-----------|-----|
| `invalid choice: 'clustering'` | Rebuild image (fixed `job_entry.py` argv) and redeploy; clear job `--command`/`--args` overrides |
| `No module named ' clustering'` | Job command was set incorrectly (extra spaces / wrong module). Use default image entrypoint only |
| `relation "articles" does not exist` | Run `alembic upgrade head` against Neon `DATABASE_URL` |
| GCS download fails | Grant Cloud Run service account `storage.objectViewer` on the bucket |
