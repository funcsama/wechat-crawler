#!/usr/bin/env python3.11
"""
daily_digest.py - 每日科技资讯报告生成 + 推送到飞书
Run as: python3 scripts/daily_digest.py

整合了：
1. fetch_rss.py - 抓取配置的信源
2. daily_report.py - 生成中文 Markdown 报告
3. 发送到飞书群
"""
import sys
import os
import json
import yaml
import time
import feedparser
import textwrap
from datetime import datetime, timezone
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_FILE = os.path.join(WORKDIR, "sources", "tech_rss.yaml")
REPORTS_DIR = os.path.join(WORKDIR, "reports")
PROXY = "http://127.0.0.1:7890"
TIMEOUT = 15
MAX_PER_SOURCE = 5
LIMIT = 20  # 总文章数


# ---------------------------------------------------------------------------
# RSS Fetcher
# ---------------------------------------------------------------------------
def fetch_feed(source: dict) -> list:
    from urllib.request import Request, urlopen
    import ssl

    url = source["url"]
    name = source["name"]
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TechDailyBot/1.0)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
    }
    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        ctx = ssl._create_unverified_context()
    except AttributeError:
        pass
    articles = []

    try:
        import urllib.request
        proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        resp = opener.open(req, timeout=TIMEOUT)
        content = resp.read()
    except Exception as e:
        print(f"[WARN] {name}: {e}", file=sys.stderr)
        return []

    d = feedparser.parse(content)
    for entry in d.entries[:MAX_PER_SOURCE]:
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published = dt.isoformat()
            except Exception:
                pass

        summary = entry.get("summary", "") or entry.get("description", "") or ""
        # Strip HTML tags from summary
        import re
        summary = re.sub(r'<[^>]+>', '', summary).strip()[:200]

        articles.append({
            "title": entry.get("title", "").strip(),
            "url": entry.get("link") or entry.get("id", ""),
            "summary": summary,
            "published": published,
            "source": name,
            "lang": source["lang"],
            "category": source["category"],
        })
    return articles


def fetch_all() -> list:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_articles = []
    enabled = [s for s in config["sources"] if s.get("enabled", True)]
    for source in enabled:
        articles = fetch_feed(source)
        all_articles.extend(articles)
        print(f"[INFO] {source['name']}: {len(articles)}", file=sys.stderr)
        time.sleep(0.2)

    all_articles.sort(key=lambda a: a["published"] or "", reverse=True)
    return all_articles[:LIMIT]


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------
CAT_EMOJI = {
    "ai": "🤖",
    "tech_startup": "🚀",
    "consumer_tech": "📱",
    "deep_tech": "🔬",
    "deep_tech_research": "🎓",
    "community": "👨‍💻",
    "tech_business": "💼",
    "open_source": "🌟",
    "digital_life": "✨",
    "tech_culture": "🌐",
}
CAT_NAME = {
    "ai": "AI",
    "tech_startup": "科技创业",
    "consumer_tech": "消费科技",
    "deep_tech": "深度技术",
    "deep_tech_research": "学术研究",
    "community": "社区",
    "tech_business": "科技商业",
    "open_source": "开源",
    "digital_life": "数字生活",
    "tech_culture": "科技文化",
}

def make_md(articles: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# 📰 每日科技资讯 {now}",
        f"共 **{len(articles)}** 条 | 信源: RSS",
        "",
    ]

    # Category stats
    cats = defaultdict(int)
    for a in articles:
        cats[a.get("category", "other")] += 1
    cat_parts = []
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1])[:6]:
        cat_parts.append(f"{CAT_EMOJI.get(cat,'📰')}{CAT_NAME.get(cat,cat)}:{cnt}")
    lines.append(" | ".join(cat_parts))
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, a in enumerate(articles, 1):
        emoji = CAT_EMOJI.get(a.get("category", ""), "📰")
        title = a["title"]
        url = a["url"]
        source = a["source"]
        lang = a["lang"]
        pub = a.get("published", "")[:10]
        summary = a.get("summary", "")

        lines.append(f"**{i}. {title}**")
        lines.append(f"📰 {source} | {'🇨🇳中文' if lang=='zh' else '🌐EN'} | 📅 {pub}")
        if summary:
            lines.append(f"{summary[:120]}{'...' if len(summary)>120 else ''}")
        lines.append(f"🔗 {url}")
        lines.append("")

    lines.append("---")
    lines.append("*🤖 AI 自动抓取生成 | wechat-crawler*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("[INFO] Fetching RSS feeds...", file=sys.stderr)
    articles = fetch_all()
    print(f"[INFO] Got {len(articles)} articles", file=sys.stderr)

    report_md = make_md(articles)

    # Save
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(REPORTS_DIR, f"daily_{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[INFO] Saved: {out_path}", file=sys.stderr)

    # Output for cron → will be sent to Feishu
    print(report_md)


if __name__ == "__main__":
    main()
