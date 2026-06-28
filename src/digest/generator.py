"""Main digest generation pipeline."""
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..storage.models import (
    ContentItem, ContentSummary, StoryCluster, ClusterMembership,
    WeeklyDigest, Source
)
from ..processing.llm import generate_executive_summary, synthesize_cluster_summary
from .markdown_renderer import render_markdown
from .html_renderer import render_html

logger = logging.getLogger(__name__)


def generate_weekly_digest(db: Session, week_start: datetime = None) -> WeeklyDigest:
    """
    Generate the weekly digest for the given week.
    week_start: Monday of the target week (defaults to last Monday)
    """
    if week_start is None:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    week_end = week_start + timedelta(days=7)

    # Get all story clusters for the week
    clusters = (
        db.query(StoryCluster)
        .filter(
            StoryCluster.week_start >= week_start,
            StoryCluster.week_start < week_end,
        )
        .all()
    )

    # For each cluster, load items and synthesize if not already done
    cluster_data = []
    for cluster in clusters:
        items = _load_cluster_items(db, cluster)
        if not cluster.synthesized_summary:
            synthesis = synthesize_cluster_summary(items)
            cluster.synthesized_summary = synthesis.get("synthesized_summary", "")
            cluster.theme_label = synthesis.get("theme_label", cluster.theme_label)
            cluster.novelty_indicator = synthesis.get("novelty_indicator", "new")
            db.add(cluster)

        cluster_data.append({
            "id": cluster.id,
            "theme_label": cluster.theme_label,
            "synthesized_summary": cluster.synthesized_summary,
            "novelty_indicator": cluster.novelty_indicator or "new",
            "sources": [i.get("source_name") for i in items],
            "hot_takes": [
                ht for i in items for ht in (i.get("hot_takes") or [])
            ],
            "items": items,
        })

    db.commit()

    # Generate executive summary
    exec_summary = generate_executive_summary(cluster_data)

    # Count sources and items
    sources_count = db.query(Source).filter(Source.active == True).count()
    items_count = (
        db.query(ContentItem)
        .filter(
            ContentItem.publish_date >= week_start,
            ContentItem.publish_date < week_end,
        )
        .count()
    )

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "executive_summary": exec_summary,
        "clusters": cluster_data,
        "sources_count": sources_count,
        "items_count": items_count,
        "generated_at": datetime.utcnow(),
    }

    markdown_content = render_markdown(context)
    html_content = render_html(context)

    week_str = week_start.strftime("%Y-%W")
    output_dir = os.environ.get("OUTPUT_DIR", "output/digests")
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, f"{week_str}-digest.md")
    html_path = os.path.join(output_dir, f"{week_str}-digest.html")

    with open(md_path, "w") as f:
        f.write(markdown_content)
    with open(html_path, "w") as f:
        f.write(html_content)

    digest = WeeklyDigest(
        week_start=week_start,
        week_end=week_end,
        sources_count=sources_count,
        items_count=items_count,
        markdown_path=md_path,
        html_path=html_path,
        markdown_content=markdown_content,
        html_content=html_content,
        executive_summary=exec_summary,
    )
    db.add(digest)
    db.commit()

    return digest


def _load_cluster_items(db: Session, cluster: StoryCluster) -> list[dict]:
    memberships = (
        db.query(ClusterMembership)
        .filter(ClusterMembership.cluster_id == cluster.id)
        .all()
    )

    items = []
    for m in memberships:
        item = db.query(ContentItem).filter(ContentItem.id == m.item_id).first()
        if not item:
            continue
        source = db.query(Source).filter(Source.id == item.source_id).first()
        summary = item.summary
        items.append({
            "title": item.title,
            "author": item.author,
            "url": item.url,
            "source_name": source.name if source else item.author,
            "source_type": source.source_type if source else "unknown",
            "publish_date": item.publish_date,
            "summary_text": summary.summary_text if summary else "",
            "key_facts": summary.key_facts if summary else [],
            "themes": summary.themes if summary else [],
            "hot_takes": summary.hot_takes if summary else [],
            "entities": summary.entities if summary else {},
            "novelty_score": summary.novelty_score if summary else 1.0,
        })

    return items
