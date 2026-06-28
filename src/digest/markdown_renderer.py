"""Render weekly digest as Markdown."""
from datetime import datetime


def render_markdown(context: dict) -> str:
    week_start: datetime = context["week_start"]
    week_end: datetime = context["week_end"]
    clusters: list[dict] = context["clusters"]
    exec_summary: list[str] = context["executive_summary"]
    sources_count: int = context["sources_count"]
    items_count: int = context["items_count"]
    generated_at: datetime = context["generated_at"]

    date_range = f"{week_start.strftime('%B %d')}–{week_end.strftime('%B %d, %Y')}"

    lines = [
        f"# Weekly Intel Digest",
        f"**Week of {date_range}** | {sources_count} sources processed | {items_count} items analyzed",
        "",
        "## 🎯 Executive Summary",
    ]
    for bullet in exec_summary:
        lines.append(f"- {bullet}")

    lines += ["", "## 📊 Key Themes This Week", ""]

    # Collect all hot takes
    all_hot_takes = []
    source_index: dict[str, dict] = {}

    for cluster in clusters:
        novelty_tag = "🆕 New" if cluster.get("novelty_indicator") == "new" else "🔄 Ongoing story"
        sources_list = ", ".join(set(filter(None, cluster.get("sources", []))))

        lines += [
            f"### {cluster['theme_label']}",
            "",
            cluster.get("synthesized_summary", ""),
            "",
            f"**Sources:** {sources_list}",
            f"**Novelty:** {novelty_tag}",
            "",
        ]

        for ht in cluster.get("hot_takes", []):
            source_name = cluster.get("sources", ["Unknown"])[0] if cluster.get("sources") else "Unknown"
            all_hot_takes.append((ht, source_name))

        for src in cluster.get("sources", []):
            if src and src not in source_index:
                item_type = "Unknown"
                for item in cluster.get("items", []):
                    if item.get("source_name") == src:
                        item_type = item.get("source_type", "Unknown").title()
                        break
                source_index[src] = {"count": 0, "type": item_type}
            if src:
                source_index[src]["count"] += 1

    # Hot takes section
    if all_hot_takes:
        lines += [
            "## 🔥 Hot Takes & Contrarian Views",
            "",
            "| Take | Source | My Assessment |",
            "|------|--------|---------------|",
        ]
        for take, source in all_hot_takes[:10]:
            take_clean = take.replace("|", "\\|")
            lines.append(f"| {take_clean} | {source} | Notable perspective |")
        lines.append("")

    # Signals section
    lines += [
        "## 📈 Signals to Watch",
        "",
    ]
    signals = [
        c["theme_label"]
        for c in clusters
        if c.get("novelty_indicator") == "new"
    ]
    for signal in signals[:5]:
        lines.append(f"- Emerging: {signal}")
    lines.append("")

    # Source index
    if source_index:
        lines += [
            "## 📚 Source Index",
            "",
            "| Source | Items | Type |",
            "|--------|-------|------|",
        ]
        for src, info in sorted(source_index.items()):
            lines.append(f"| {src} | {info['count']} | {info['type']} |")
        lines.append("")

    lines += [
        "---",
        f"*Generated {generated_at.strftime('%Y-%m-%d %H:%M UTC')} by Weekly Intel*",
    ]

    return "\n".join(lines)
