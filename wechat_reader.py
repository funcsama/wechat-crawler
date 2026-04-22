#!/usr/bin/env python3.11
"""
WeChat Article Reader - 微信公众号文章爬取工具
基于 sanfan3/wechat-article-reader 思路，适配本服务器环境

核心策略：
1. HTTP 直接请求（可能有验证码墙）
2. Playwright 浏览器回退（绕过 IP 限制）
3. 正则解析提取内容

用法:
    python wechat_reader.py <url>
    python wechat_reader.py --no-browser <url>   # 仅 HTTP
"""
import sys
import json
import re
import html as htmlmod
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROXY = "http://127.0.0.1:7890"  # mihomo 代理

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)
REFERER = "https://mp.weixin.qq.com/"
TIMEOUT = 20

# ---------------------------------------------------------------------------
# HTML Fetch
# ---------------------------------------------------------------------------
def fetch_html(url: str, use_proxy: bool = True) -> tuple[Optional[str], int | None]:
    """HTTP fetch with proxy support."""
    headers = {
        "User-Agent": UA,
        "Referer": REFERER,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = Request(url, headers=headers, method="GET")
    ctx = ssl.create_default_context()

    proxies = {"http": PROXY, "https": PROXY} if use_proxy else None

    try:
        if proxies:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler(proxies)
            opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                return html, getattr(resp, "status", 200)
        else:
            with urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                return html, getattr(resp, "status", 200)
    except HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, None


# ---------------------------------------------------------------------------
# Browser Fetch
# ---------------------------------------------------------------------------
def fetch_html_via_browser(url: str) -> tuple[Optional[str], int | None]:
    """Headless browser fallback using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        ctx = browser.new_context(
            user_agent=UA,
            locale="zh-CN",
            extra_http_headers={"Referer": REFERER},
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT * 1000)
        except Exception:
            pass
        try:
            page.wait_for_selector("#js_content", timeout=8000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        html = page.content()
        browser.close()
        return html, None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_wechat_html(html: str) -> dict:
    """Extract title, author, pub_time, content_html, images, links from WeChat article HTML."""
    # title
    title = ""
    m = re.search(r'<h2[^>]*id="activity-name"[^>]*>(.*?)</h2>', html, re.S | re.I)
    if m:
        title = re.sub(r'<[^>]+>', "", m.group(1)).strip()
    if not title:
        m = re.search(r'property="og:title"[^>]*content="(.*?)"', html, re.I)
        if m:
            title = m.group(1).strip()

    # author
    author = ""
    m = re.search(r'id="js_name"[^>]*>(.*?)</', html, re.S | re.I)
    if m:
        author = re.sub(r'<[^>]+>', "", m.group(1)).strip()
    if not author:
        m = re.search(r'name="author"[^>]*content="(.*?)"', html, re.I)
        if m:
            author = m.group(1).strip()

    # published time
    pub_time = ""
    m = re.search(r'property="article:published_time"[^>]*content="(.*?)"', html, re.I)
    if m:
        pub_time = m.group(1).strip()
    if not pub_time:
        m = re.search(r'var\s+ct\s*=\s*"(\d{10})"\s*;', html)
        if m:
            try:
                ts = int(m.group(1))
                pub_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            except Exception:
                pass

    # main content
    content_html = ""
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.S | re.I)
    if m:
        content_html = m.group(1)
        # normalize lazy-load attributes
        content_html = re.sub(r'<img([^>]*?)data-src="(.*?)"', r'<img\1src="\2"', content_html)
        content_html = re.sub(r'<img([^>]*?)data-original="(.*?)"', r'<img\1src="\2"', content_html)
        content_html = re.sub(r'<img([^>]*?)data-backup-src="(.*?)"', r'<img\1src="\2"', content_html)

    # collect images
    images = []
    for im in re.findall(r'<img[^>]*src="(.*?)"', content_html, re.I):
        images.append(htmlmod.unescape(im))
    for im in re.findall(r'<img[^>]*data-src="(.*?)"', content_html, re.I):
        images.append(htmlmod.unescape(im))
    for im in re.findall(r'<img[^>]*data-original="(.*?)"', content_html, re.I):
        images.append(htmlmod.unescape(im))
    for im in re.findall(r'<img[^>]*data-backup-src="(.*?)"', content_html, re.I):
        images.append(htmlmod.unescape(im))
    # deduplicate
    seen = set()
    dedup_images = []
    for im in images:
        if im and im not in seen:
            seen.add(im)
            dedup_images.append(im)

    # collect links
    links = []
    for a in re.findall(r'<a[^>]*href="(.*?)"', content_html, re.I):
        links.append(htmlmod.unescape(a))

    return {
        "title": title,
        "author": author,
        "pub_time": pub_time,
        "content_html": content_html,
        "images": dedup_images,
        "links": list(dict.fromkeys(links)),
    }


def html_to_text(html: str) -> str:
    """Simple HTML to text conversion."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = htmlmod.unescape(text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


def html_to_markdown(html: str, title: str = "", author: str = "") -> str:
    """Convert WeChat article HTML to minimal Markdown."""
    import textwrap
    lines = []
    if title:
        lines.append(f"# {title}\n")
    if author:
        lines.append(f"**作者**: {author}\n")
    if lines:
        lines.append("---\n")

    content_html = ""
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.S | re.I)
    if m:
        content_html = m.group(1)

    # paragraphs
    for p in re.findall(r'<p[^>]*>(.*?)</p>', content_html, re.S | re.I):
        text = re.sub(r'<[^>]+>', '', p)
        text = htmlmod.unescape(text).strip()
        if text:
            lines.append(text + "\n")

    # blockquotes
    for bq in re.findall(r'<blockquote[^>]*>(.*?)</blockquote>', content_html, re.S | re.I):
        text = re.sub(r'<[^>]+>', '', bq)
        text = htmlmod.unescape(text).strip()
        if text:
            lines.append(f"> {text}\n")

    # h1-h4
    for lvl in range(1, 5):
        for h in re.findall(rf'<h{lvl}[^>]*>(.*?)</h{lvl}>', content_html, re.S | re.I):
            text = re.sub(r'<[^>]+>', '', h)
            text = htmlmod.unescape(text).strip()
            if text:
                lines.append(f"{'#' * lvl} {text}\n")

    # images
    for img in re.findall(r'<img[^>]*src="(.*?)"[^>]*>', content_html, re.I):
        if img and not img.startswith("data:"):
            lines.append(f"![img]({img})\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Reader
# ---------------------------------------------------------------------------
def read_wechat_article(url: str, use_browser: bool = True) -> dict:
    """
    Read a WeChat public account article.
    Returns dict with: title, author, pub_time, content_md, content_text, images, links, source_url, strategy
    """
    from urllib.parse import urlparse

    if not url.startswith("https://mp.weixin.qq.com/s"):
        return {"error": "invalid_url", "message": "URL must be public mp.weixin.qq.com/s link", "source_url": url}

    # Clean tracking params
    url = re.sub(r'\?.*', '', url)

    # Try HTTP first
    html, status = fetch_html(url, use_proxy=True)
    strategy = "http"
    logs = {"http_status": status}

    if html and 'id="js_content"' in html:
        parsed = parse_wechat_html(html)
        if parsed["title"]:
            strategy = "http"
            logs["http_ok"] = True
        else:
            html = None

    # Browser fallback
    if not html and use_browser:
        html, _ = fetch_html_via_browser(url)
        strategy = "browser"
        logs["browser_used"] = True

    if not html:
        # Last resort: plain text if it's a verification page
        return {
            "error": "fetch_failed",
            "message": "Could not fetch article (blocked by WeChat). Try from a residential IP.",
            "source_url": url,
            "strategy": strategy,
        }

    parsed = parse_wechat_html(html)
    if not parsed["title"]:
        return {
            "error": "parse_failed",
            "message": "Article HTML fetched but could not parse content",
            "source_url": url,
            "html_preview": html[:500],
        }

    content_text = html_to_text(parsed["content_html"])
    content_md = html_to_markdown(html, parsed["title"], parsed["author"])

    return {
        "title": parsed["title"],
        "author": parsed["author"],
        "pub_time": parsed["pub_time"],
        "content_md": content_md,
        "content_text": content_text[:1000] + ("..." if len(content_text) > 1000 else ""),
        "images": parsed["images"],
        "links": parsed["links"],
        "source_url": url,
        "strategy": strategy,
        "logs": logs,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    use_browser = "--no-browser" not in sys.argv

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[-1]
    if not url.startswith("http"):
        print(f"错误: 最后一个参数应为 URL，当前为: {url}")
        sys.exit(1)

    result = read_wechat_article(url, use_browser=use_browser)

    if "error" in result:
        print(f"\n❌ 获取失败: {result['error']}")
        print(f"   原因: {result.get('message', 'Unknown')}")
        print(f"   URL: {result.get('source_url', url)}")
        sys.exit(1)

    print(f"\n✅ 获取成功 ({result['strategy']})\n")
    print(f"标题: {result['title']}")
    print(f"作者: {result['author']}")
    print(f"时间: {result['pub_time']}")
    print(f"图片: {len(result['images'])} 张")
    print(f"链接: {len(result['links'])} 个")
    print(f"\n{'='*60}")
    print(f"正文（前800字）:\n{result['content_text'][:800]}\n...")
    print(f"\n{'='*60}")
    print(f"\nMarkdown 输出:\n{result['content_md'][:600]}\n...")
