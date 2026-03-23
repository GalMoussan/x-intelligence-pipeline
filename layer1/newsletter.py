"""Layer 1: HTML newsletter builder — render Jinja2 template with Claude output."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings


def _markdown_to_html(md: str) -> str:
    """
    Minimal Markdown → HTML converter (no external deps).
    Handles: h1–h3, bold, italic, inline code, blockquote, unordered lists, paragraphs.
    """
    lines = md.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        # Headings
        if line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{_inline(line[2:])}</h1>")
        # Blockquote
        elif line.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<blockquote style="border-left:3px solid #ccc;margin:8px 0;padding:4px 12px;color:#555;">{_inline(line[2:])}</blockquote>')
        # Unordered list item
        elif re.match(r"^[-*] ", line):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
        # Numbered list item
        elif re.match(r"^\d+\. ", line):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r"^\d+\. ", "", line)
            num = re.match(r"^\d+", line).group()
            html_lines.append(f'<p style="margin:4px 0;"><strong>{num}.</strong> {_inline(content)}</p>')
        # Blank line
        elif line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")
        # Paragraph
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{_inline(line)}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline(text: str) -> str:
    """Apply inline Markdown: bold, italic, inline code, @handles, #hashtags."""
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r'<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;">\1</code>', text)
    # @handles → X profile links
    text = re.sub(r"@(\w+)", r'<a href="https://x.com/\1" style="color:#1d9bf0;text-decoration:none;">@\1</a>', text)
    return text


def _pick_top_tweets(corpus: dict[str, list[dict]], n: int = 5) -> list[dict]:
    """Return the top n tweets by like count across all accounts."""
    import json

    all_tweets = []
    for username, tweets in corpus.items():
        for t in tweets:
            metrics = json.loads(t["metrics"]) if t.get("metrics") else {}
            all_tweets.append({
                "username": username,
                "text": t["text"],
                "created_at": t["created_at"][:10],
                "likes": metrics.get("like_count", 0),
                "url": f"https://x.com/{username}/status/{t['id']}",
            })

    all_tweets.sort(key=lambda x: x["likes"], reverse=True)
    return all_tweets[:n]


def build_newsletter(
    analysis: dict,
    corpus: dict[str, list[dict]] | None = None,
) -> str:
    """
    Render the newsletter HTML.

    Args:
        analysis: Output from analyzer.analyze_tweets() — contains 'markdown' and 'week_date'.
        corpus:   Optional scraper corpus used to pull top source tweets.

    Returns:
        Rendered HTML string.
    """
    week_date = analysis["week_date"]
    body_html = _markdown_to_html(analysis["markdown"])
    top_tweets = _pick_top_tweets(corpus, n=5) if corpus else []

    env = Environment(
        loader=FileSystemLoader(settings.TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("newsletter.html")

    return template.render(
        week_date=week_date,
        body_html=body_html,
        top_tweets=top_tweets,
    )
