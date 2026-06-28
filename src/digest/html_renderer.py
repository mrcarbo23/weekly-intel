"""Render weekly digest as HTML email."""
from datetime import datetime


def render_html(context: dict) -> str:
    week_start: datetime = context["week_start"]
    week_end: datetime = context["week_end"]
    clusters: list[dict] = context["clusters"]
    exec_summary: list[str] = context["executive_summary"]
    sources_count: int = context["sources_count"]
    items_count: int = context["items_count"]
    generated_at: datetime = context["generated_at"]

    date_range = f"{week_start.strftime('%B %d')}–{week_end.strftime('%B %d, %Y')}"

    # Executive summary links
    exec_items = "".join(
        f'<li><a href="#theme-{i}" style="color:#0066cc;">{bullet}</a></li>'
        for i, bullet in enumerate(exec_summary)
    )

    # Theme sections
    theme_sections = ""
    all_hot_takes = []
    source_rows = {}

    for i, cluster in enumerate(clusters):
        is_new = cluster.get("novelty_indicator", "new") == "new"
        tag_style = (
            "background:#d4edda;color:#155724;" if is_new
            else "background:#fff3cd;color:#856404;"
        )
        tag_text = "🆕 New" if is_new else "🔄 Ongoing"
        sources_html = ", ".join(
            f'<a href="#" style="color:#0066cc;">{s}</a>'
            for s in set(filter(None, cluster.get("sources", [])))
        )

        theme_sections += f"""
    <section id="theme-{i}" style="background:#f8f9fa;border-radius:8px;padding:16px;margin:16px 0;">
      <span style="{tag_style}padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">{tag_text}</span>
      <h3 style="margin:8px 0;font-size:18px;">{cluster['theme_label']}</h3>
      <p style="margin:8px 0;line-height:1.6;">{cluster.get('synthesized_summary', '')}</p>
      <p style="font-size:14px;color:#666;margin-top:12px;">📎 Sources: {sources_html}</p>
    </section>"""

        for ht in cluster.get("hot_takes", []):
            src = cluster.get("sources", ["Unknown"])[0] if cluster.get("sources") else "Unknown"
            all_hot_takes.append((ht, src))

        for src in cluster.get("sources", []):
            if src:
                if src not in source_rows:
                    source_type = "Unknown"
                    for item in cluster.get("items", []):
                        if item.get("source_name") == src:
                            source_type = item.get("source_type", "Unknown").title()
                            break
                    source_rows[src] = {"count": 0, "type": source_type}
                source_rows[src]["count"] += 1

    # Hot takes HTML
    hot_takes_html = ""
    for take, source in all_hot_takes[:8]:
        hot_takes_html += f"""
      <div style="border-left:4px solid #dc3545;padding-left:12px;margin:12px 0;">
        <p style="margin:0;"><strong>{source}:</strong> {take}</p>
      </div>"""

    # Source table
    source_table_rows = "".join(
        f"<tr><td style='padding:4px 8px;'>{src}</td>"
        f"<td style='padding:4px 8px;text-align:center;'>{info['count']}</td>"
        f"<td style='padding:4px 8px;'>{info['type']}</td></tr>"
        for src, info in sorted(source_rows.items())
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <title>Weekly Intel - Week of {date_range}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: 28px; margin-bottom: 4px; }}
    h2 {{ font-size: 20px; border-bottom: 2px solid #eee; padding-bottom: 6px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ background: #f0f0f0; padding: 6px 8px; text-align: left; font-size: 13px; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #1a1a1a; color: #e0e0e0; }}
      section[style*='background:#f8f9fa'] {{ background: #2d2d2d !important; }}
      .sources {{ color: #aaa; }}
      th {{ background: #333; }}
      h2 {{ border-color: #444; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header style="border-bottom:3px solid #0066cc;padding-bottom:16px;margin-bottom:24px;">
      <h1>📬 Weekly Intel</h1>
      <p style="color:#666;margin:0;">Week of {date_range} &bull; {sources_count} sources &bull; {items_count} items analyzed</p>
    </header>

    <section style="background:#e8f4fd;border-radius:8px;padding:16px;margin:16px 0;">
      <h2 style="margin-top:0;">🎯 This Week in 30 Seconds</h2>
      <ul style="margin:0;padding-left:20px;">
        {exec_items}
      </ul>
    </section>

    <h2>📊 Key Themes This Week</h2>
    {theme_sections}

    <section style="margin:24px 0;">
      <h2>🔥 Hot Takes &amp; Contrarian Views</h2>
      {hot_takes_html if hot_takes_html else '<p style="color:#888;">No notable hot takes this week.</p>'}
    </section>

    <section style="margin:24px 0;">
      <h2>📚 Source Index</h2>
      <table>
        <tr><th>Source</th><th>Items</th><th>Type</th></tr>
        {source_table_rows}
      </table>
    </section>

    <footer style="border-top:1px solid #eee;margin-top:32px;padding-top:16px;">
      <p style="font-size:13px;color:#888;margin:0;">
        Generated {generated_at.strftime('%Y-%m-%d %H:%M UTC')} by Weekly Intel &bull;
        <a href="#" style="color:#0066cc;">View archive</a> &bull;
        <a href="#" style="color:#0066cc;">Unsubscribe</a>
      </p>
    </footer>
  </div>
</body>
</html>"""
