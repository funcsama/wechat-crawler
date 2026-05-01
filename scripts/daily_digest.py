#!/usr/bin/env python3.11
"""
daily_digest.py - 每日科技资讯报告生成 + 直接推送到飞书（不经过 LLM）
Run as: python3.11 scripts/daily_digest.py
"""
import sys
import os
import json
import yaml
import time
import feedparser
import requests
from datetime import datetime, timezone, timedelta
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

# 飞书配置 — 直接发送，不经过 LLM
FEISHU_APP_ID = "cli_a9257489d7f95cb0"
FEISHU_APP_SECRET = "Z0yMxON3tFvMs3hrPvnsjeUQCc7wCZwW"
FEISHU_CHAT_ID = "oc_d170dda09264716d786cd28cc48e5f78"  # 3号资讯群

CST = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# RSS Fetcher
# ---------------------------------------------------------------------------
def fetch_feed(source: dict) -> list:
    import urllib.request, ssl, re

    url = source["url"]
    name = source["name"]
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TechDailyBot/1.0)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl._create_unverified_context()

    try:
        proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        resp = opener.open(req, timeout=TIMEOUT)
        content = resp.read()
    except Exception as e:
        print(f"[WARN] {name}: {e}", file=sys.stderr)
        return []

    d = feedparser.parse(content)
    articles = []
    for entry in d.entries[:MAX_PER_SOURCE]:
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published = dt.isoformat()
            except Exception:
                pass

        summary = entry.get("summary", "") or entry.get("description", "") or ""
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
    "ai": "🤖", "tech_startup": "🚀", "consumer_tech": "📱",
    "deep_tech": "🔬", "deep_tech_research": "🎓", "community": "👨‍💻",
    "tech_business": "💼", "open_source": "🌟", "digital_life": "✨",
    "tech_culture": "🌐",
}
CAT_NAME = {
    "ai": "AI", "tech_startup": "科技创业", "consumer_tech": "消费科技",
    "deep_tech": "深度技术", "deep_tech_research": "学术研究", "community": "社区",
    "tech_business": "科技商业", "open_source": "开源", "digital_life": "数字生活",
    "tech_culture": "科技文化",
}

def make_report(articles: list) -> str:
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    lines = [
        f"📰 每日科技资讯 · {datetime.now(CST).strftime('%Y-%m-%d')}",
        f"共 {len(articles)} 条 | 自动抓取自 RSS",
        "",
    ]

    cats = defaultdict(int)
    for a in articles:
        cats[a.get("category", "other")] += 1
    cat_parts = [f"{CAT_EMOJI.get(c,'📰')}{CAT_NAME.get(c,c)}:{n}"
                 for c, n in sorted(cats.items(), key=lambda x: -x[1])[:5]]
    lines.append("  ".join(cat_parts))
    lines.append("")

    for i, a in enumerate(articles, 1):
        title = a["title"]
        url = a["url"]
        source = a["source"]
        lang = "🇨🇳" if a["lang"] == "zh" else "🌐"
        pub = a.get("published", "")[:10]
        summary = a.get("summary", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   {lang} {source} · {pub}")
        if summary:
            lines.append(f"   {summary[:100]}{'...' if len(summary) > 100 else ''}")
        lines.append(f"   {url}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Feishu Sender
# ---------------------------------------------------------------------------
def get_feishu_token() -> str:
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10,
    )
    return r.json().get("tenant_access_token", "")


def send_to_feishu(text: str) -> bool:
    token = get_feishu_token()
    if not token:
        print("[ERROR] 获取飞书 token 失败", file=sys.stderr)
        return False

    r = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=15,
    )
    result = r.json()
    if result.get("code") == 0:
        print("[INFO] 飞书发送成功", file=sys.stderr)
        return True
    else:
        print(f"[ERROR] 飞书发送失败: {result}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("[INFO] Fetching RSS feeds...", file=sys.stderr)
    articles = fetch_all()
    print(f"[INFO] Got {len(articles)} articles", file=sys.stderr)

    if not articles:
        print("[WARN] 没有抓到任何文章，跳过发送", file=sys.stderr)
        return

    report = make_report(articles)

    # 保存本地存档
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today = datetime.now(CST).strftime("%Y-%m-%d")
    out_path = os.path.join(REPORTS_DIR, f"daily_{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[INFO] Saved: {out_path}", file=sys.stderr)

    # 直接发飞书，不经过 LLM
    send_to_feishu(report)


if __name__ == "__main__":
    main()
