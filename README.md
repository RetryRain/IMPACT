# IMPACT - Semantic News Aggregation Pipeline

A serverless, AI-powered news aggregation platform that transforms thousands of daily articles into coherent, semantically organized news stories. Built with modern cloud infrastructure and cutting-edge ML/NLP techniques.

## 🎯 Overview

IMPACT solves the fundamental challenge of news aggregation: **duplicate coverage and information fragmentation**. Instead of relying on fragile URL matching or simple text comparison, it uses semantic understanding to group identical events and synthesize comprehensive news stories.

### What Makes IMPACT Different

- **Semantic Event Clustering**: Groups news articles by meaning using all-MiniLM-L6-v2 embeddings and pgvector ANN, not by URL or keywords
- **Cost-Optimized AI Pipeline**: Two-stage LLM inference strategy (DeepSeek/OpenRouter) minimizes costs while maximizing quality
- **Serverless Architecture**: Cloud Run Jobs auto-scale to process thousands of articles daily with 60% infrastructure cost reduction
- **SEO-First PWA**: Next.js 15 with dynamic OG images, JSON-LD NewsArticle schemas, and Google News sitemaps

## 🏗️ System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   News Sources  │────▶│   Scrapy Crawler │────▶│  Cloud Run Jobs     │
│  (RSS, APIs,    │     │   (Serverless)   │     │  (ML Inference)     │
│   Web Scraping) │     └──────────────────┘     └─────────────────────┘
└─────────────────┘              │                          │
                                 ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────────┐
                        │  PostgreSQL +    │     │  Semantic Clustering│
                        │  pgvector        │◀────│  all-MiniLM-L6-v2  │
                        │  (ANN Indexes)   │     │  + Cosine Threshold│
                        └──────────────────┘     └─────────────────────┘
                                 │
                                 ▼
                        ┌──────────────────────────────────────────────┐
                        │     Two-Stage LLM Pipeline                 │
                        │  Stage 1: Semantic Synthesis (DeepSeek)    │
                        │  Stage 2: Event Consolidation (OpenRouter) │
                        └──────────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌──────────────────────────────────────────────┐
                        │  Next.js 15 PWA (React 19, Drizzle,        │
                        │  Serwist)                                  │
                        │  - Dynamic OG Images                      │
                        │  - JSON-LD NewsArticle schemas           │
                        │  - Google News sitemaps                  │
                        │  - Offline-first caching                │
                        │  - Dynamic 301 redirects                │
                        └──────────────────────────────────────────────┘
```

## 🧠 Core Technical Components

### Semantic Clustering Engine
Uses all-MiniLM-L6-v2 sentence transformers to generate embeddings for each article, then applies cosine similarity thresholds with pgvector's ANN indexes to group identical events. This achieves **95% deduplication accuracy** without fragile URL or keyword matching.

### Two-Stage LLM Pipeline
Cost-optimized inference strategy that reduces API costs by ~40%:
- **Stage 1**: Lightweight semantic synthesis using DeepSeek to identify key themes
- **Stage 2**: Comprehensive event consolidation using OpenRouter for final story generation

### Serverless ETL Pipeline
- Scrapy-based crawlers running on Cloud Run Jobs
- Scheduled execution with auto-scaling
- Processes 5,000+ articles daily with no always-on infrastructure costs

### Frontend Architecture
- Next.js 15 with React 19 and App Router
- Drizzle ORM for type-safe database operations
- Serwist for offline-first PWA capabilities
- Dynamic OG image generation for social sharing
- JSON-LD structured data for NewsArticle schema
- Automated Google News sitemaps
- Dynamic 301 redirects for URL canonicalization

## 📊 Performance Characteristics

| Metric | Achievement |
|--------|------------|
| Daily Processing | 5,000+ articles |
| Deduplication Accuracy | 95% using semantic clustering |
| Infrastructure Cost | 60% reduction vs. always-on servers |
| Semantic Search Latency | ~200ms with pgvector ANN |

## 🛠️ Technology Stack

**Backend & Infrastructure**
- Scrapy for web crawling
- Cloud Run Jobs for serverless container orchestration
- PostgreSQL with pgvector extension
- all-MiniLM-L6-v2 for sentence embeddings
- DeepSeek & OpenRouter for LLM inference
- Google Cloud Platform

**Frontend**
- Next.js 15 with App Router
- React 19
- Drizzle ORM
- Serwist for service workers
- Vercel for deployment

## 🔑 Key Design Decisions

1. **Semantic over Syntactic**: Chose embeddings over URL matching or keyword deduplication for superior event grouping
2. **Serverless over Always-On**: Cloud Run Jobs reduce costs while maintaining throughput
3. **Two-Stage LLM**: Balances cost and quality by separating synthesis from consolidation
4. **SEO First**: Built search engine optimization into the frontend architecture from day one

## 🚀 Deployment Strategy

- **Backend**: Deployed as Cloud Run Jobs with scheduled triggers
- **Frontend**: Deployed on Vercel with edge functions for dynamic routing
- **Database**: Managed PostgreSQL with automated backups
- **CI/CD**: Automated pipeline for testing and deployment

## 📁 Project Structure

```
impact/
├── backend/
│   ├── scrapers/        # Scrapy spiders for news sources
│   ├── ml/             # Embedding generation and clustering
│   ├── llm/            # Two-stage LLM pipeline
│   └── cloud/          # Cloud Run job definitions
├── frontend/
│   ├── app/            # Next.js 15 App Router
│   ├── components/     # React 19 components
│   ├── lib/           # Drizzle ORM and utilities
│   └── public/        # Static assets
├── infrastructure/
│   ├── terraform/      # IaC for cloud resources
│   └── docker/         # Container configurations
└── database/
    ├── migrations/     # Schema migrations
    └── seeds/         # Initial data
```

## 🤔 Why This Architecture?

**Problem**: Traditional news aggregation relies on URL deduplication, which fails when the same story is covered by different outlets with unique URLs and varying headlines.

**Solution**: Semantic understanding through embeddings catches stories about the same event regardless of how they're written or where they're published.

**Cost Consideration**: Processing thousands of articles through LLMs is expensive. The two-stage pipeline cuts costs by using lightweight inference for initial processing and reserved heavier inference only for consolidated stories.

**Scale**: Serverless architecture means the pipeline can handle traffic spikes (e.g., breaking news) without over-provisioning resources.
