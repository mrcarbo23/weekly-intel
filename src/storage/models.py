"""SQLAlchemy ORM models for Weekly Intel."""
from datetime import datetime
from typing import Optional
import json
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean,
    ForeignKey, Index, JSON, LargeBinary
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # substack, gmail, youtube
    url = Column(String(1024))
    config = Column(JSON)  # source-specific config (gmail sender filter, etc.)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_fetched_at = Column(DateTime)
    items = relationship("ContentItem", back_populates="source")


class ContentItem(Base):
    __tablename__ = "content_items"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    title = Column(String(1024))
    author = Column(String(255))
    url = Column(String(1024))
    publish_date = Column(DateTime)
    raw_content = Column(Text)
    content_hash = Column(String(64), unique=True)  # SHA-256 for exact dedup
    minhash_signature = Column(LargeBinary)  # Pickled MinHash for fuzzy dedup
    simhash_value = Column(String(64))
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    source = relationship("Source", back_populates="items")
    summary = relationship("ContentSummary", back_populates="item", uselist=False)
    cluster_memberships = relationship("ClusterMembership", back_populates="item")


class ContentSummary(Base):
    __tablename__ = "content_summaries"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("content_items.id"), unique=True)
    key_facts = Column(JSON)  # List of key new facts
    themes = Column(JSON)  # List of themes
    hot_takes = Column(JSON)  # List of contrarian views
    entities = Column(JSON)  # Named entities: companies, people, technologies
    summary_text = Column(Text)
    embedding = Column(LargeBinary)  # Pickled numpy array
    novelty_score = Column(Float)  # 0-1, higher = more novel
    created_at = Column(DateTime, default=datetime.utcnow)
    item = relationship("ContentItem", back_populates="summary")


class StoryCluster(Base):
    __tablename__ = "story_clusters"
    id = Column(Integer, primary_key=True)
    week_start = Column(DateTime, nullable=False)
    canonical_item_id = Column(Integer, ForeignKey("content_items.id"))
    theme_label = Column(String(512))
    synthesized_summary = Column(Text)
    novelty_indicator = Column(String(10))  # "new" or "ongoing"
    previous_cluster_id = Column(Integer, ForeignKey("story_clusters.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    memberships = relationship("ClusterMembership", back_populates="cluster")
    canonical_item = relationship("ContentItem", foreign_keys=[canonical_item_id])


class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    cluster_id = Column(Integer, ForeignKey("story_clusters.id"), nullable=False)
    similarity_score = Column(Float)
    item = relationship("ContentItem", back_populates="cluster_memberships")
    cluster = relationship("StoryCluster", back_populates="memberships")


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"
    id = Column(Integer, primary_key=True)
    week_start = Column(DateTime, nullable=False, unique=True)
    week_end = Column(DateTime, nullable=False)
    sources_count = Column(Integer, default=0)
    items_count = Column(Integer, default=0)
    markdown_path = Column(String(1024))
    html_path = Column(String(1024))
    markdown_content = Column(Text)
    html_content = Column(Text)
    executive_summary = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)
    delivery_logs = relationship("DeliveryLog", back_populates="digest")


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"
    id = Column(Integer, primary_key=True)
    digest_id = Column(Integer, ForeignKey("weekly_digests.id"), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    provider = Column(String(50))  # resend, sendgrid, ses
    status = Column(String(50))  # sent, failed, pending
    message_id = Column(String(255))
    error_message = Column(Text)
    attempts = Column(Integer, default=0)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    digest = relationship("WeeklyDigest", back_populates="delivery_logs")


# Indexes for performance
Index("idx_content_items_source_date", ContentItem.source_id, ContentItem.publish_date)
Index("idx_content_items_hash", ContentItem.content_hash)
Index("idx_content_items_simhash", ContentItem.simhash_value)
Index("idx_story_clusters_week", StoryCluster.week_start)
