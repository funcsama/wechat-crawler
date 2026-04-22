#!/usr/bin/env python3
"""
fetch_rss.py - 抓取配置的 RSS 源列表
用法: python3 scripts/fetch_rss.py [--limit 5]
输出: JSON 格式的文章列表
"""
import sys
import os
import json
import yaml
import time
import feedparser
from datetime import datetime, timezone
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SOURCES_FILE = os.path.join(os.path.dirname(__file__), "..", "sources", "tech_rss.yaml")
PROXY = "http://127.0.0.1:7890"
TIMEOUT = 15
MAX_PER_SOURCE = 5  # 每源最多取多少条


def fetch_feed(source: dict) -> list:
    """抓取单个 RSS 源，返回文章列表。"""
    url = source["url"]
    name = source["name"]

    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    import ssl

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TechDailyBot/1.0)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
    }
    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()

    articles = []
    try:
        import urllib.request
        proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        resp = opener.open(req, timeout=TIMEOUT)
        content = resp.read()
    except Exception as e:
        print(f"[WARN] {name}: fetch failed - {e}", file=sys.stderr)
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

        article = {
            "title": entry.get("title", "").strip(),
            "url": entry.get("link") or entry.get("id", ""),
            "summary": entry.get("summary", "").strip(),
            "published": published,
            "source": name,
            "lang": source["lang"],
            "category": source["category"],
        }
        articles.append(article)

    return articles


def main():
    limit = 5
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        limit = int(sys.argv[idx + 1])

    # Load sources
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_articles = []
    source_count = 0
    enabled_sources = [s for s in config["sources"] if s.get("enabled", True)]

    for source in enabled_sources:
        source_count += 1
        articles = fetch_feed(source)
        all_articles.extend(articles)
        print(f"[INFO] {source['name']}: fetched {len(articles)} articles", file=sys.stderr)
        time.sleep(0.3)  # Be polite

    # Sort by published time (most recent first)
    all_articles.sort(key=lambda a: a["published"] or "", reverse=True)

    # Limit total
    all_articles = all_articles[:limit * len(enabled_sources)]

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources_queried": source_count,
        "total_articles": len(all_articles),
        "articles": all_articles,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
