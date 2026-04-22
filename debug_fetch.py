#!/usr/bin/env python3.11
"""Debug script to see what we actually get back from WeChat."""
import sys
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import ssl

PROXY = "http://127.0.0.1:7890"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)

url = "https://mp.weixin.qq.com/s/hz0SosxuMSHlNgzB3yWrjQ"
headers = {
    "User-Agent": UA,
    "Referer": "https://mp.weixin.qq.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
req = Request(url, headers=headers, method="GET")
ctx = ssl.create_default_context()

import urllib.request
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

try:
    with opener.open(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        print("Status:", getattr(resp, "status", 200))
        print("URL:", resp.url)
        print("HTML length:", len(html))
        print("First 300 chars:", html[:300])
        print("\nLast 300 chars:", html[-300:])

        print("\n--- Markers ---")
        marker_js = 'id="js_content"' in html
        print("has js_content:", marker_js)
        marker_og = "og:title" in html
        print("has og:title:", marker_og)
        marker_env = "环境异常" in html
        print("has 环境异常:", marker_env)
        marker_vc = "verifycode" in html
        print("has verifycode:", marker_vc)

        m = re.search(r"<div[^>]*id=\"js_content\"[^>]*>", html[:500], re.I)
        print("found js_content opening tag at position:", m.start() if m else "NOT FOUND")

        m2 = re.search(r'property="og:title"[^>]*', html, re.I)
        if m2:
            print("og:title match:", m2.group(0))
        else:
            print("og:title match: NOT FOUND")

except HTTPError as e:
    print("HTTPError:", e.code)
    print(e.read().decode("utf-8", errors="ignore")[:500])
except Exception as e:
    print("Error:", e)
