"""Story clustering using embeddings - Layer 2."""
import logging
from datetime import datetime
from typing import Optional
import numpy as np
from sqlalchemy.orm import Session
from ..storage.models import ContentItem, ContentSummary, StoryCluster, ClusterMembership
from .embeddings import deserialize_embedding, cosine_similarity

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85


def cluster_week_items(db: Session, week_start: datetime, week_end: datetime) -> list[StoryCluster]:
    """
    Cluster all processed items for a given week into story clusters.
    Uses cosine similarity on embeddings.
    Returns list of created/updated StoryCluster objects.
    """
    # Fetch items with summaries and embeddings
    items = (
        db.query(ContentItem)
        .join(ContentSummary)
        .filter(
            ContentItem.publish_date >= week_start,
            ContentItem.publish_date < week_end,
            ContentSummary.embedding.isnot(None),
        )
        .all()
    )

    if not items:
        return []

    embeddings = []
    valid_items = []
    for item in items:
        if item.summary and item.summary.embedding:
            emb = deserialize_embedding(item.summary.embedding)
            embeddings.append(emb)
            valid_items.append(item)

    if not valid_items:
        return []

    clusters = _greedy_cluster(valid_items, embeddings)

    db_clusters = []
    for cluster_items in clusters:
        # Pick canonical item: earliest publish date
        canonical = min(
            cluster_items,
            key=lambda x: x.publish_date or datetime.max
        )

        theme = canonical.summary.themes[0] if canonical.summary and canonical.summary.themes else "General"

        cluster = StoryCluster(
            week_start=week_start,
            canonical_item_id=canonical.id,
            theme_label=theme,
        )
        db.add(cluster)
        db.flush()

        for item in cluster_items:
            emb_a = deserialize_embedding(canonical.summary.embedding)
            emb_b = deserialize_embedding(item.summary.embedding)
            sim = cosine_similarity(emb_a, emb_b)
            membership = ClusterMembership(
                item_id=item.id,
                cluster_id=cluster.id,
                similarity_score=sim,
            )
            db.add(membership)

        db_clusters.append(cluster)

    db.commit()
    return db_clusters


def _greedy_cluster(items: list, embeddings: list[np.ndarray]) -> list[list]:
    """Simple greedy clustering by cosine similarity threshold."""
    n = len(items)
    assigned = [False] * n
    clusters = []

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [items[i]]
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            sim = cosine_similarity(embeddings[i], embeddings[j])
            if sim >= SIMILARITY_THRESHOLD:
                cluster.append(items[j])
                assigned[j] = True
        clusters.append(cluster)

    return clusters


def check_historical_novelty(
    db: Session,
    item: ContentItem,
    weeks_back: int = 4,
) -> float:
    """
    Check how novel an item is vs the past N weeks.
    Returns novelty score 0-1 (1 = completely new).
    """
    from datetime import timedelta
    if not item.summary or not item.summary.embedding:
        return 1.0

    cutoff = item.publish_date - timedelta(weeks=weeks_back) if item.publish_date else None
    if not cutoff:
        return 1.0

    old_summaries = (
        db.query(ContentSummary)
        .join(ContentItem)
        .filter(
            ContentItem.publish_date >= cutoff,
            ContentItem.publish_date < item.publish_date,
            ContentSummary.embedding.isnot(None),
            ContentItem.id != item.id,
        )
        .all()
    )

    if not old_summaries:
        return 1.0

    item_emb = deserialize_embedding(item.summary.embedding)
    max_sim = max(
        cosine_similarity(item_emb, deserialize_embedding(s.embedding))
        for s in old_summaries
    )

    return 1.0 - max_sim
