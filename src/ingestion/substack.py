"""Substack RSS ingestion."""
import hashlib
import logging
from datetime import datetime
from typing import Optional
import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_substack_feed(url: str) -> list[dict]:
    """
    Fetch articles from a Substack RSS feed.
    url: RSS feed URL (e.g. https://stratechery.com/feed) or Substack URL
         (auto-converted to feed URL)
    Returns list of article dicts.
    """
    feed_url = _normalize_feed_url(url)
    feed = feedparser.parse(feed_url)

    articles = []
    for entry in feed.entries:
        content = _extract_content(entry)
        articles.append({
            "title": entry.get("title", ""),
            "author": entry.get("author", feed.feed.get("author", "")),
            "url": entry.get("link", ""),
            "publish_date": _parse_date(entry),
            "raw_content": content,
            "source_name": feed.feed.get("title", url),
        })
    return articles


def _normalize_feed_url(url: str) -> str:
    """Convert Substack homepage URL to RSS feed URL."""
    url = url.rstrip("/")
    if url.endswith("/feed"):
        return url
    if "substack.com" in url or not url.endswith(".xml"):
        return f"{url}/feed"
    return url


def _extract_content(entry) -> str:
    """Extract clean text content from feed entry."""
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content = entry.summary

    if content:
        soup = BeautifulSoup(content, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    return ""


def _parse_date(entry) -> Optional[datetime]:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
    except Exception:
        pass
    return datetime.utcnow()
