#!/usr/bin/env python3
"""
daily_report.py - 生成每日科技资讯报告
用法: python3 scripts/daily_report.py [--articles PATH] [--limit 20]
"""
import sys
import os
import json
import yaml
import textwrap
from datetime import datetime, timezone
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ARTICLES_PATH = None  # 默认从 stdin 读 fetch_rss.py 输出
for i, arg in enumerate(sys.argv):
    if arg == "--articles" and i + 1 < len(sys.argv):
        ARTICLES_PATH = sys.argv[i + 1]
    if arg == "--limit" and i + 1 < len(sys.argv):
        global LIMIT
        LIMIT = int(sys.argv[i + 1])

LIMIT = 20


def load_articles(path=None) -> list:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    return data.get("articles", [])


def group_by_source(articles: list) -> dict:
    groups = defaultdict(list)
    for a in articles:
        groups[a["source"]].append(a)
    return dict(groups)


def format_article(article: dict, idx: int) -> str:
    """将单篇文章格式化为带序号的 Markdown 条目。"""
    title = article["title"]
    url = article["url"]
    summary = article.get("summary", "")[:200]
    source = article["source"]
    lang = article["lang"]
    published = article.get("published", "")[:10]

    emoji = "🤖" if article.get("category") == "ai" else "💻"
    lines = [
        f"{idx}. {emoji} **{title}**",
        f"   📰 {source} | 🌍 {'中文' if lang == 'zh' else '英文'} | 📅 {published}",
    ]
    if summary:
        lines.append(f"   {summary[:150]}{'...' if len(summary) > 150 else ''}")
    lines.append(f"   🔗 {url}")
    return "\n".join(lines)


def generate_report(articles: list, fetched_at: str) -> str:
    """生成 Markdown 格式的每日报告。"""
    now_cst = datetime.now(timezone.utc).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    total = len(articles)

    # 按分类统计
    categories = defaultdict(int)
    for a in articles:
        categories[a.get("category", "other")] += 1

    lines = [
        f"# 📰 每日科技资讯 ({now_cst} UTC)",
        "",
        f"共抓取 **{total}** 条文章，来自以下分类：",
        "",
    ]

    # 分类概览
    cat_emoji = {
        "tech_startup": "🚀",
        "consumer_tech": "📱",
        "deep_tech": "🔬",
        "deep_tech_research": "🎓",
        "ai": "🤖",
        "community": "👨‍💻",
        "tech_business": "💼",
        " open_source": "🌟",
        "digital_life": "✨",
        "tech_culture": "🌐",
    }
    cat_names = {
        "tech_startup": "科技创业",
        "consumer_tech": "消费科技",
        "deep_tech": "深度技术",
        "deep_tech_research": "学术研究",
        "ai": "AI",
        "community": "社区",
        "tech_business": "科技商业",
        "open_source": "开源",
        "digital_life": "数字生活",
        "tech_culture": "科技文化",
    }
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        emoji = cat_emoji.get(cat, "📰")
        name = cat_names.get(cat, cat)
        lines.append(f"- {emoji} {name}: {count} 条")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📋 今日文章列表")
    lines.append("")

    for i, article in enumerate(articles[:LIMIT], 1):
        lines.append(format_article(article, i))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*🤖 由 AI 自动抓取生成 | 信源：RSS feeds | 系统：wechat-crawler*")

    return "\n".join(lines)


def main():
    articles = load_articles(ARTICLES_PATH)
    if not articles:
        print("[ERROR] No articles loaded", file=sys.stderr)
        sys.exit(1)

    # 限制
    articles = articles[:LIMIT]

    report = generate_report(articles, "")

    # 输出到文件
    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(report_dir, f"daily_{today}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 也输出到 stdout
    print(report)
    print(f"\n[INFO] Report saved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
