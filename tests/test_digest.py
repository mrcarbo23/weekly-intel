import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from src.digest.markdown_renderer import render_markdown
from src.digest.html_renderer import render_html

MOCK_CONTEXT = {
    "week_start": datetime(2024, 1, 1),
    "week_end": datetime(2024, 1, 7),
    "executive_summary": ["AI regulation is heating up", "Startup funding rebounds"],
    "clusters": [
        {
            "id": 1,
            "theme_label": "AI Regulation",
            "synthesized_summary": "According to TechCrunch, the EU passed new AI rules. Wired adds that penalties are significant.",
            "novelty_indicator": "new",
            "sources": ["TechCrunch", "Wired"],
            "hot_takes": ["This will kill innovation"],
            "items": [
                {
                    "source_name": "TechCrunch",
                    "source_type": "substack",
                    "title": "EU AI Act Passes",
                    "novelty_score": 0.9,
                }
            ],
        }
    ],
    "sources_count": 3,
    "items_count": 12,
    "generated_at": datetime(2024, 1, 7, 12, 0),
}


def test_markdown_render():
    md = render_markdown(MOCK_CONTEXT)
    assert "# Weekly Intel Digest" in md
    assert "AI Regulation" in md
    assert "🎯 Executive Summary" in md
    assert "🔥 Hot Takes" in md
    assert "AI regulation is heating up" in md


def test_html_render():
    html = render_html(MOCK_CONTEXT)
    assert "<!DOCTYPE html>" in html
    assert "Weekly Intel" in html
    assert "AI Regulation" in html
    assert "prefers-color-scheme: dark" in html


def test_markdown_has_source_index():
    md = render_markdown(MOCK_CONTEXT)
    assert "📚 Source Index" in md
    assert "TechCrunch" in md


def test_html_has_executive_summary():
    html = render_html(MOCK_CONTEXT)
    assert "30 Seconds" in html
    assert "AI regulation is heating up" in html
