from __future__ import annotations

from typing import Protocol

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from clustering.config import get_settings
from clustering.db.models import Article, ArticleEmbedding
from clustering.log import info
from clustering.text import build_embedding_text, hash_embedding_text

_model = None


class EmbeddingModel(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray: ...


def get_model() -> EmbeddingModel:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        info(
            f"Loading embedding model ({settings.embedding_model}) — "
            "first run downloads weights and can take 1–2 minutes ..."
        )
        _model = SentenceTransformer(settings.embedding_model)
        info("Embedding model ready.")
    return _model


def set_model(model: EmbeddingModel) -> None:
    global _model
    _model = model


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, get_settings().embedding_dim), dtype=np.float32)

    settings = get_settings()
    vectors = get_model().encode(
        texts,
        batch_size=settings.batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def _purge_stale_model_embeddings(session: Session) -> int:
    settings = get_settings()
    result = session.execute(
        delete(ArticleEmbedding).where(
            ArticleEmbedding.model_name != settings.embedding_model
        )
    )
    return result.rowcount or 0


def embed_articles(session: Session, *, limit: int | None = None) -> dict[str, int]:
    settings = get_settings()
    purged = _purge_stale_model_embeddings(session)
    if purged:
        info(f"Removed {purged} embeddings from a previous model.")

    query = (
        select(Article)
        .outerjoin(ArticleEmbedding, ArticleEmbedding.article_id == Article.id)
        .where(ArticleEmbedding.article_id.is_(None))
        .order_by(Article.published_at.asc().nulls_last(), Article.created_at.asc())
    )
    if limit is not None:
        query = query.limit(limit)

    articles = list(session.scalars(query))
    pending: list[tuple[Article, str, str]] = []

    info(f"Embedding {len(articles)} articles missing vectors ...")
    for article in articles:
        text = build_embedding_text(article.title, article.summary, article.body)
        if not text:
            continue
        text_hash = hash_embedding_text(text)
        pending.append((article, text, text_hash))

    embedded = 0

    if pending:
        info(
            f"Encoding {len(pending)} articles "
            f"(batch size {settings.batch_size}) ..."
        )

    for start in range(0, len(pending), settings.batch_size):
        batch = pending[start : start + settings.batch_size]
        texts = [entry[1] for entry in batch]
        vectors = embed_texts(texts)

        for (article, _text, text_hash), vector in zip(batch, vectors, strict=True):
            article.embedding = ArticleEmbedding(
                article_id=article.id,
                model_name=settings.embedding_model,
                dim=settings.embedding_dim,
                embedding=vector.tolist(),
                text_hash=text_hash,
            )
            embedded += 1

        done = min(start + settings.batch_size, len(pending))
        info(f"  embedded {done}/{len(pending)}")

    skipped = len(articles) - embedded
    session.flush()
    return {"embedded": embedded, "skipped": skipped, "examined": len(articles)}
