#!/usr/bin/env python3.11
"""Test WeChat without proxy."""
from urllib.request import Request, urlopen
import ssl, re

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)

# Try direct (no proxy)
url = "https://mp.weixin.qq.com/s/hz0SosxuMSHlNgzB3yWrjQ"
req = Request(url, headers={
    "User-Agent": UA,
    "Referer": "https://mp.weixin.qq.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})
ctx = ssl.create_default_context()

try:
    with urlopen(req, timeout=20, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        print("Direct (no proxy) result:")
        print("Status:", getattr(resp, "status", 200))
        print("URL:", resp.url)
        print("Length:", len(html))
        print("Has js_content:", 'id="js_content"' in html)
        print("Has 环境异常:", "环境异常" in html)
        print("First 200:", html[:200])
except Exception as e:
    print("Direct error:", e)
