"""LLM processing using Claude API for summarization and extraction."""
import json
import logging
import os
from typing import Any
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def extract_content_insights(text: str, title: str = "", author: str = "") -> dict:
    """
    Extract structured insights from a piece of content.
    Returns dict with: key_facts, themes, hot_takes, entities, summary_text
    """
    prompt = f"""Analyze this content and extract structured insights.

Title: {title}
Author: {author}

Content (truncated to 6000 chars):
{text[:6000]}

Return a JSON object with exactly these fields:
{{
  "summary_text": "2-3 sentence summary of the main point",
  "key_facts": ["list of 3-5 specific, novel facts or announcements"],
  "themes": ["list of 2-4 broad themes or topics (e.g. 'AI regulation', 'startup funding')"],
  "hot_takes": ["list of contrarian or opinion-driven claims, if any"],
  "entities": {{
    "companies": ["company names mentioned"],
    "people": ["person names mentioned"],
    "technologies": ["technology names mentioned"]
  }}
}}

Focus on genuinely NEW information, not recycled commentary."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text_response = response.content[0].text
    # Extract JSON from response
    start = text_response.find("{")
    end = text_response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text_response[start:end])
    raise ValueError(f"Could not parse JSON from LLM response: {text_response[:200]}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def synthesize_cluster_summary(cluster_items: list[dict]) -> dict:
    """
    Synthesize a single summary for a story cluster.
    cluster_items: list of dicts with keys: title, author, source_name, summary_text, hot_takes
    Returns dict with: synthesized_summary, theme_label, novelty_indicator
    """
    items_text = "\n\n".join([
        f"Source: {item.get('source_name', item.get('author', 'Unknown'))}\n"
        f"Title: {item.get('title', '')}\n"
        f"Summary: {item.get('summary_text', '')}\n"
        f"Hot takes: {'; '.join(item.get('hot_takes', []))}"
        for item in cluster_items
    ])

    prompt = f"""Multiple sources covered the same story. Synthesize them into a unified summary.

Sources:
{items_text}

Return JSON:
{{
  "theme_label": "Short theme name (5-8 words max)",
  "synthesized_summary": "Unified summary that: (1) leads with the canonical fact, (2) notes what each source adds uniquely, (3) highlights any divergent perspectives. Use format: 'According to [Source], [key point]. [Source B] adds that [detail]. [Source C] takes a different view, arguing [contrarian point].' 3-5 sentences.",
  "hot_takes": ["list of notable contrarian takes across all sources"],
  "novelty_indicator": "new or ongoing"
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text_response = response.content[0].text
    start = text_response.find("{")
    end = text_response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text_response[start:end])
    raise ValueError(f"Could not parse JSON: {text_response[:200]}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_executive_summary(clusters: list[dict]) -> list[str]:
    """Generate 3-5 bullet point executive summary from story clusters."""
    clusters_text = "\n".join([
        f"- {c.get('theme_label', '')}: {c.get('synthesized_summary', '')[:200]}"
        for c in clusters[:10]
    ])

    prompt = f"""Given these story clusters from this week's content, write 3-5 executive summary bullet points.

Clusters:
{clusters_text}

Return JSON array of strings (the bullet points):
["bullet 1", "bullet 2", "bullet 3"]

Each bullet should be 1-2 sentences, factual, and highlight why it matters."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    text_response = response.content[0].text
    start = text_response.find("[")
    end = text_response.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text_response[start:end])
    return ["Unable to generate executive summary"]
