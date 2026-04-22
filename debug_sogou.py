#!/usr/bin/env python3.11
"""Try fetching the WeChat article via Sogou."""
import re
from urllib.request import Request, urlopen
import ssl
from urllib.parse import quote

PROXY = "http://127.0.0.1:7890"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)

# Search Sogou for this specific article
keyword = "hz0SosxuMSHlNgzB3yWrjQ"
sogou_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(keyword)}&ie=utf8"

headers = {
    "User-Agent": UA,
    "Referer": "https://weixin.sogou.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

import urllib.request
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
ctx = ssl.create_default_context()
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

req = Request(sogou_url, headers=headers)
try:
    with opener.open(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        print("Sogou status:", getattr(resp, "status", 200))
        print("HTML length:", len(html))

        # Parse results
        from lxml import etree
        page = etree.HTML(html)
        lis = page.xpath('//ul[@class="news-list"]/li')
        print(f"Found {len(lis)} results")

        for li in lis[:5]:
            # Get title/link
            a_els = li.xpath('.//a[contains(@href, "link?url=")]')
            if a_els:
                a = a_els[0]
                title = re.sub(r'<[^>]+>', '', a.text or '').strip()
                href = a.get('href', '')
                print(f"Title: {title}")
                print(f"Href: {href}")
                print()

        # Also try to find article links
        all_links = re.findall(r'link\?url=(https?://[^\s"<>]+)', html)
        for link in all_links[:5]:
            print("Article link candidate:", link[:100])

except Exception as e:
    print("Error:", e)
