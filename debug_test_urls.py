#!/usr/bin/env python3.11
"""Test a different WeChat article to see if crawler works without captcha."""
from urllib.request import Request, urlopen
import ssl, re

PROXY = "http://127.0.0.1:7890"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)

# Try a very common article - "微信公开课" or similar
test_urls = [
    "https://mp.weixin.qq.com/s/QlQGZjBbVJbEWT8CQVfBLg",  # common test
]

import urllib.request
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
ctx = ssl.create_default_context()
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

for url in test_urls:
    req = Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://mp.weixin.qq.com/",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        with opener.open(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            print(f"URL: {url}")
            print(f"  Final URL: {resp.url}")
            print(f"  Length: {len(html)}")
            print(f"  Has js_content: {'id=\"js_content\"' in html}")
            print(f"  Has 环境异常: {'环境异常' in html}")
            if 'id="js_content\"' in html:
                m = re.search(r'<h2[^>]*id="activity-name"[^>]*>(.*?)</h2>', html, re.S | re.I)
                print(f"  Title: {re.sub(r\"<[^>]+\", \"\", m.group(1)).strip() if m else \"not found\"}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
