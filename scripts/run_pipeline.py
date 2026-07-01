#!/usr/bin/env python3
"""Main pipeline script: ingest → process → cluster → digest."""
import argparse
import hashlib
import logging
import os
import pickle
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db, get_db
from src.storage.models import Source, ContentItem, ContentSummary
from src.ingestion.substack import fetch_substack_feed
from src.ingestion.gmail import fetch_newsletters
from src.ingestion.youtube import fetch_channel_videos
from src.processing.fingerprint import (
    compute_content_hash, compute_minhash, compute_simhash,
    is_near_duplicate
)
from src.processing.embeddings import get_embedding, serialize_embedding
from src.processing.clustering import cluster_week_items, check_historical_novelty
from src.processing.llm import extract_content_insights
from src.digest.generator import generate_weekly_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def ingest_source(db, source: Source) -> int:
    """Fetch and store content from a source. Returns count of new items."""
    logger.info(f"Ingesting source: {source.name} ({source.source_type})")

    items = []
    if source.source_type == "substack":
        if not source.url:
            raise ValueError("substack source has no URL configured")
        items = fetch_substack_feed(source.url)
    elif source.source_type == "gmail":
        config = source.config or {}
        items = fetch_newsletters(
            senders=config.get("senders"),
            label=config.get("label", "Newsletters"),
            days_back=config.get("days_back", 7),
        )
    elif source.source_type == "youtube":
        if not source.url:
            raise ValueError("youtube source has no URL configured")
        config = source.config or {}
        items = fetch_channel_videos(source.url, max_videos=config.get("max_videos", 10))

    new_count = 0
    for item_data in items:
        content = item_data.get("raw_content", "")
        if len(content) < 100:
            continue

        content_hash = compute_content_hash(content)

        # Layer 1: exact dedup
        existing = db.query(ContentItem).filter(
            ContentItem.content_hash == content_hash
        ).first()
        if existing:
            continue

        # Layer 1: near-duplicate check via MinHash
        minhash = compute_minhash(content)
        recent_items = db.query(ContentItem).filter(
            ContentItem.source_id == source.id
        ).order_by(ContentItem.created_at.desc()).limit(50).all()

        is_dup = False
        for recent in recent_items:
            if recent.minhash_signature and is_near_duplicate(minhash, recent.minhash_signature):
                logger.debug(f"Near-duplicate detected, skipping: {item_data.get('title')}")
                is_dup = True
                break

        if is_dup:
            continue

        db_item = ContentItem(
            source_id=source.id,
            title=item_data.get("title", ""),
            author=item_data.get("author", ""),
            url=item_data.get("url", ""),
            publish_date=item_data.get("publish_date"),
            raw_content=content,
            content_hash=content_hash,
            minhash_signature=minhash,
            simhash_value=compute_simhash(content),
            processed=False,
        )
        db.add(db_item)
        new_count += 1

    source.last_fetched_at = datetime.utcnow()
    db.add(source)
    db.commit()
    logger.info(f"  → {new_count} new items from {source.name}")
    return new_count


def process_items(db) -> int:
    """Run LLM extraction on unprocessed items."""
    unprocessed = db.query(ContentItem).filter(ContentItem.processed == False).all()
    logger.info(f"Processing {len(unprocessed)} items with LLM...")

    count = 0
    for item in unprocessed:
        try:
            insights = extract_content_insights(
                text=item.raw_content,
                title=item.title,
                author=item.author,
            )

            embedding = get_embedding(insights.get("summary_text", item.raw_content[:500]))
            novelty = check_historical_novelty(db, item)

            summary = ContentSummary(
                item_id=item.id,
                key_facts=insights.get("key_facts", []),
                themes=insights.get("themes", []),
                hot_takes=insights.get("hot_takes", []),
                entities=insights.get("entities", {}),
                summary_text=insights.get("summary_text", ""),
                embedding=serialize_embedding(embedding),
                novelty_score=novelty,
            )
            db.add(summary)
            item.processed = True
            db.add(item)
            db.commit()
            count += 1
        except Exception as e:
            logger.error(f"Failed to process item {item.id}: {e}")
            db.rollback()

    return count


def add_source(db, name: str, source_type: str, url: str, config: dict = None):
    source = Source(name=name, source_type=source_type, url=url, config=config)
    db.add(source)
    db.commit()
    logger.info(f"Added source: {name}")
    return source


def main():
    parser = argparse.ArgumentParser(description="Weekly Intel Pipeline")
    parser.add_argument("command", choices=["ingest", "process", "cluster", "digest", "full", "add-source"])
    parser.add_argument("--week-start", help="Week start date YYYY-MM-DD")
    parser.add_argument("--name", help="Source name (for add-source)")
    parser.add_argument("--type", dest="source_type", help="Source type: substack|gmail|youtube")
    parser.add_argument("--url", help="Source URL")
    args = parser.parse_args()

    init_db()

    with get_db() as db:
        if args.command == "add-source":
            add_source(db, args.name, args.source_type, args.url)

        elif args.command == "ingest":
            sources = db.query(Source).filter(Source.active == True).all()
            for source in sources:
                ingest_source(db, source)

        elif args.command == "process":
            count = process_items(db)
            logger.info(f"Processed {count} items")

        elif args.command == "cluster":
            week_start = datetime.utcnow()
            if args.week_start:
                week_start = datetime.strptime(args.week_start, "%Y-%m-%d")
            from datetime import timedelta
            week_end = week_start + timedelta(days=7)
            clusters = cluster_week_items(db, week_start, week_end)
            logger.info(f"Created {len(clusters)} story clusters")

        elif args.command == "digest":
            week_start = None
            if args.week_start:
                week_start = datetime.strptime(args.week_start, "%Y-%m-%d")
            digest = generate_weekly_digest(db, week_start)
            logger.info(f"Digest generated: {digest.markdown_path}")

        elif args.command == "full":
            # Run complete pipeline
            sources = db.query(Source).filter(Source.active == True).all()
            for source in sources:
                ingest_source(db, source)
            process_items(db)
            from datetime import timedelta
            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            cluster_week_items(db, week_start, week_end)
            digest = generate_weekly_digest(db, week_start)
            logger.info(f"Full pipeline complete. Digest: {digest.markdown_path}")


if __name__ == "__main__":
    main()
