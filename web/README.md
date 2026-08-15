# Bytez Web — public news PWA

SEO-first Next.js reader for synthesized stories from the Neon publish database (`synthesized_stories`). No accounts, read-only.

## Stack

- **Next.js 15** (App Router, SSR/ISR)
- **Tailwind CSS**
- **Drizzle ORM** + Neon serverless driver
- **Serwist** PWA (installable, offline shell)

## Setup

```bash
cd web
cp .env.example .env
# Set SYNTHESIS_DATABASE_URL (same publish DB as clustering synthesis)
# Set NEXT_PUBLIC_SITE_URL (e.g. http://localhost:3000)
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Database migration (slug column)

The web app expects `slug` on `synthesized_stories` (publish migration `003`). Apply all publish migrations before first run:

```bash
cd ../clustering
alembic -c alembic_publish.ini upgrade head
```

If Alembic is not on your PATH, from `web/`:

```bash
node scripts/apply-publish-migration.mjs
```

That script applies migration `003` (slug backfill) and stamps `alembic_version`.

## Routes

| Path | Description |
|------|-------------|
| `/` | Home feed (priority → recency) |
| `/tamil-nadu`, `/india`, `/world` | Scope hubs |
| `/{scope}/{slug}` | Article page (canonical SEO URL) |
| `/s/{id}` | 301 redirect to canonical article URL |
| `/rss.xml` | RSS (last 50 stories) |
| `/sitemap.xml` | Standard sitemap |
| `/news-sitemap.xml` | Google News sitemap (48h) |
| `/api/stories` | JSON feed for PWA refresh |

## SEO

- Per-article `title`, description, canonical, Open Graph, Twitter cards
- Dynamic OG images at `/{scope}/{slug}/opengraph-image`
- JSON-LD `NewsArticle` on every article
- Paginated list pages with `rel=prev/next`
- `robots.txt` allows crawling

Set production canonicals via `NEXT_PUBLIC_SITE_URL` (no trailing slash).

## Deploy on Vercel

1. Import the repo; set **Root Directory** to `web`.
2. Environment variables:
   - `SYNTHESIS_DATABASE_URL` — Neon **pooled** publish DB URL (`postgres://` or `postgresql+psycopg://` both work)
   - `NEXT_PUBLIC_SITE_URL` — `https://your-domain.com`
3. Deploy. Vercel runs `npm run build` automatically.

### Neon connection

Use the same database as `clustering` synthesis (`SYNTHESIS_DATABASE_URL`). Prefer Neon’s **pooler** endpoint for serverless.

## PWA

- `manifest.webmanifest` + Serwist service worker (`public/sw.js` after build)
- Install from browser menu (“Add to Home Screen”)
- HTML pages use network-first caching; shell is precached for offline navigation

## Feed ordering (matches synthesis)

Stories are ordered by `priority DESC, published_at DESC` — editorial score from the LLM, not article count.
